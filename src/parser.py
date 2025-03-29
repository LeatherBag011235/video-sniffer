from playwright.async_api import async_playwright  
import asyncio  
import re


async def click_player3_play_button(page_url):
    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=False,
            # Human-like browser fingerprints
            channel="chrome",  # Uses actual Chrome browser
            args=[
            ]
        )
        
        # Create context with human-like parameters
        context = await browser.new_context(
            viewport=None,  # Random viewport
            locale='en-US',
            timezone_id='America/New_York',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            permissions=['geolocation']
        )
        
        page = await context.new_page()
        
        # 1. NAVIGATE TO TARGET PAGE --------------------------
        await page.goto(page_url)
        
        # 2. SELECT PLAYER 3 TAB ------------------------------
        try:
            await page.locator('span[onclick*="player-3"]').click()
            print("Selected Player 3")
            
        except:
            print("Failed to select Player 3 automatically")
            await page.pause()  # Pauses execution for manual intervention
        
        segments = {}

        segment_num_pattern = re.compile(r'segment(\d+)')
        
        def capture_segments(request):
            if '.ts' in request.url:
                match = segment_num_pattern.search(request.url)
                if match:
                    segment_num = match.group(1)
                    print(segment_num)
                    segments[segment_num] = request.url
                
                print(f"Captured segment: {request.url.split('/')[-1][:20]}...")
        
        page.on('request', capture_segments)
        print("Waiting for video segments (close browser to stop)...")
   
            
        try:
            while True:
                if page.is_closed():
                    print("Page closed - stopping capture")
                    break
                await asyncio.sleep(3)
        except Exception as e:
            print(f"Error occurred: {e}")
        finally:
            # Cleanup
            if not page.is_closed():
                await page.close()
            await browser.close()

        print(segments)


# Execute the function
asyncio.run(click_player3_play_button(
    "https://me.lordfilm12.ru/filmy/52878-jelektricheskij-shtat-2025.html"
))