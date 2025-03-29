import asyncio
import logging
from pathlib import Path
from typing import Dict, Any

from core.utils import configure_logging
from sniffer_class.captures import VideoIndexCapturer, parse_m3u8_file
from sniffer_class.gluer import VideoSegmentGluer


async def get_index_link() -> str:
    async with VideoIndexCapturer() as capturer:
        index_link: str = await capturer.get_index_url()

    return index_link


def download_cli(save_dir: Path, output_filename: str) -> None:
    configure_logging()
    logging.info("Starting to download.\nOutput Directory: %s\nFilename: %s" % (str(save_dir), output_filename))

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    index_url: str = loop.run_until_complete(get_index_link())
    hrefs: Dict[str, str] = parse_m3u8_file(index_url=index_url)
    gluer: VideoSegmentGluer = VideoSegmentGluer(
        segment_links=hrefs, save_dir=save_dir
    )
    gluer.process(output_filename=output_filename, cleanup=True)


def download_ui(save_dir: Path, output_filename: str, meta: Dict[str, Any]) -> None:
    configure_logging()
    logging.info("Starting to download.\nOutput Directory: %s\nFilename: %s" % (str(save_dir), output_filename))

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    index_url: str = loop.run_until_complete(get_index_link())
    hrefs: Dict[str, str] = parse_m3u8_file(index_url=index_url)
    gluer: VideoSegmentGluer = VideoSegmentGluer(
        segment_links=hrefs, save_dir=save_dir
    )
    gluer.process(output_filename=output_filename, cleanup=True, meta=meta)
