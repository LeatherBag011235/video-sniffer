import sys 
sys.path.append(r"C:\Users\Maxim Shibanov\Projects_Py\video-sniffer\src")

import asyncio

from sniffer_class.video_segment_capturer import VideoSegmentCapturer

async def main():
    async with VideoSegmentCapturer() as capturer:
        segments = await capturer.run(
            "https://me.lordfilm12.ru/filmy/52878-jelektricheskij-shtat-2025.html"
        )
        print(segments)   

if __name__ == "__main__":
    asyncio.run(main())
