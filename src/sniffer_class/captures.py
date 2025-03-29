# pylint: disable=attribute-defined-outside-init

import asyncio
import logging
import re
from typing import Any, Pattern, Dict, List

import requests
from playwright.async_api import async_playwright, Browser, Page, Request


def parse_m3u8_file(index_url: str) -> Dict[str, str]:
    resp = requests.get(url=index_url)
    parsed_ts_urls: List[str] = [href for href in resp.text.split("\n") if href.startswith("https://")]
    logging.info("Captured %s fragments", len(parsed_ts_urls))
    return {str(i): href for i, href in enumerate(parsed_ts_urls)}


class VideoIndexCapturer:
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
        self.segments: dict[str, str] = {}
        self.segment_num_pattern: Pattern[str] = re.compile(r'segment(\d+)')
        self.playwright: Any | None = None
        self.browser: Browser | None = None
        self.context: Any | None = None
        self.page: Page | None = None

    async def __aenter__(self) -> "VideoIndexCapturer":
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
        if request.url.endswith(".m3u8"):
            self.index_link: str = request.url

    async def get_index_url(self) -> str:
        """Go the main page and select the film that you want. Returns string url with index file"""
        await self.page.goto(url="https://me.lordfilm12.ru/")

        self.page.on('request', self.capture_segments)
        logging.info("Waiting for video segments (close browser to stop)...")

        while True:
            if self.page.is_closed():
                logging.info("Page closed - stopping capture")
                break
            await asyncio.sleep(1)

        return self.index_link
