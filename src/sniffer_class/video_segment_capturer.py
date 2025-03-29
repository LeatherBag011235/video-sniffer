import asyncio
import re
from typing import Any, Pattern
from playwright.async_api import async_playwright, Browser, Page, Request

class VideoSegmentCapturer:
    """A sophisticated video segment capturer for streaming websites using Playwright.
    
    This class provides automated capturing of .ts video segments from streaming sites with:
    - Human-like browser interaction
    - Smart resource management
    - Comprehensive error handling
    - Cross-platform compatibility
    
    Typical usage:
        async with VideoSegmentCapturer() as capturer:
            segments = await capturer.run("https://stream-site.example/video")
            if segments:
                process_segments(segments)
    """

    def __init__(self) -> None:
        """Initialize a new VideoSegmentCapturer instance with default configurations.
        
        Initializes:
        - segments: Dictionary to store captured segments in format {segment_number: url}
        - segment_num_pattern: Compiled regex to extract segment numbers from URLs
        - playwright: Placeholder for Playwright instance (set during context entry)
        - browser: Placeholder for Browser instance (set during context entry)
        - context: Placeholder for Browser Context (set during context entry)
        - page: Placeholder for Page instance (set during context entry)
        """
        self.segments: dict[str, str] = {}
        self.segment_num_pattern: Pattern[str] = re.compile(r'segment(\d+)')
        self.playwright: Any | None = None
        self.browser: Browser | None = None
        self.context: Any | None = None
        self.page: Page | None = None

    async def __aenter__(self) -> 'VideoSegmentCapturer':
        """Asynchronous context manager entry point.
        
        Initializes and configures all required Playwright resources:
        1. Launches a Chromium browser with anti-detection settings
        2. Creates a new browser context with human-like parameters
        3. Opens a new browser page/tab
        
        Returns:
            VideoSegmentCapturer: The fully initialized instance
            
        Raises:
            PlaywrightError: If browser initialization fails
        """
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=False,
            channel="chrome",
            args=[
                "--disable-blink-features=AutomationControlled",  # Avoid bot detection
                "--start-maximized"  # Appear as normal user session
            ]
        )
        self.context = await self.browser.new_context(
            viewport=None,  # Random viewport size
            locale='en-US',
            timezone_id='America/New_York',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...',
            permissions=['geolocation']  # Mimic real browser permissions
        )
        self.page = await self.context.new_page()
        return self

    async def __aexit__(self, exc_type: Any | None, exc_val: Any | None, exc_tb: Any | None) -> None:
        """Asynchronous context manager exit point.
        
        Ensures proper resource cleanup in this specific order:
        1. Current page (if still open)
        2. Browser context
        3. Browser instance
        4. Playwright instance
        
        Args:
            exc_type: Type of exception if one occurred within the context
            exc_val: Exception instance if one occurred
            exc_tb: Traceback if an exception occurred
            
        Note:
            This method is automatically called when exiting the 'async with' block,
            regardless of whether an exception occurred.
        """
        if self.page and not self.page.is_closed():
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    def capture_segments(self, request: Request) -> None:
        """Network request callback handler for capturing video segments.
        
        Analyzes each network request and captures those containing video segments (.ts files).
        Stores captured segments in self.segments dictionary with their numeric identifiers.
        
        Args:
            request: The Playwright Request object containing request details
            
        Processing Logic:
        1. Filters requests for URLs containing '.ts'
        2. Extracts segment number using regex pattern
        3. Stores valid segments in self.segments dictionary
        4. Prints capture confirmation with segment number
        """
        if '.ts' in request.url:
            match = self.segment_num_pattern.search(request.url)
            if match:
                segment_num = match.group(1)
                print(f"Segment {segment_num} captured")
                self.segments[segment_num] = request.url

    async def run(self, page_url: str) -> dict[str, str] | None:
        """Main execution method for video segment capture process.
        
        Orchestrates the complete workflow:
        1. Page navigation
        2. Player selection
        3. Segment capture
        4. Resource management
        
        Args:
            page_url: The URL of the video page to process
            
        Returns:
            dict[str, str] | None: Dictionary of captured segments in format {segment_number: url},
            or None if the operation failed
            
        Workflow Details:
        1. Navigates to specified URL
        2. Attempts automatic player selection (with manual fallback)
        3. Sets up network monitoring
        4. Waits for video segments while handling page closure
        5. Returns collected segments or None on failure
        """
        try:
            await self.page.goto(page_url)

            try:
                await self.page.locator('span[onclick*="player-3"]').click()
                print("Selected Player 3 automatically")
            except:
                print("Failed to select Player 3 automatically - awaiting manual selection")
                await self.page.pause()  # Allows manual interaction

            self.page.on('request', self.capture_segments)
            print("Waiting for video segments (close browser to stop)...")

            while True:
                if self.page.is_closed():
                    print("Page closed - stopping capture")
                    break
                await asyncio.sleep(1)

            return self.segments

        except Exception as e:
            print(f"Error occurred during capture: {e}")
            return None