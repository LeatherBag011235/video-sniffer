import asyncio
import logging
import multiprocessing
import re
import threading
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from os import PathLike
from pathlib import Path
from re import Pattern
from tkinter import ttk, filedialog, messagebox
from typing import Dict, Any, List, Optional, Literal

import requests
from playwright.async_api import Browser, Page, async_playwright, Request
from requests.adapters import HTTPAdapter
from tqdm import tqdm
from urllib3 import Retry


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


class VideoSegmentGluer:
    def __init__(
            self,
            segment_links: Dict[str, str],
            save_dir: PathLike = Path('C:/Video_Sniffer/saved_videos/'),
            max_workers: int | None = None,
            max_retries: int = 3,
            timeout: int | float = 30.0,
            pool_connections: int | None = None,
            pool_maxsize: int | None = None
    ) -> None:
        """
        Initialize the VideoSegmentGluer with automatic thread detection and connection pooling.

        Args:
            segment_links: Dictionary mapping segment numbers to URLs
            save_dir: Directory to save the final video (Path or str)
            max_workers: Number of threads to use (default: CPU count * 2)
            max_retries: Maximum number of retries for failed downloads
            timeout: Request timeout in seconds (float or int)
            pool_connections: Number of connection pools (default: max_workers)
            pool_maxsize: Maximum connections per pool (default: max_workers)
        """
        self.segment_links = segment_links
        self.save_dir = Path(save_dir) if isinstance(save_dir, str) else save_dir
        self.temp_dir = self.save_dir / 'temp_segments'
        self.timeout = float(timeout)

        # Thread pool configuration
        self.max_workers = max_workers if max_workers is not None else multiprocessing.cpu_count()
        self.max_retries = max_retries

        # Connection pool configuration
        self.pool_connections = pool_connections or self.max_workers
        self.pool_maxsize = pool_maxsize or self.max_workers

        # Create custom session with connection pooling
        self.session = self._create_session()

        # Create directories if they don't exist
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def _create_session(self) -> requests.Session:
        """Create a custom requests session with retry logic and connection pooling."""
        session = requests.Session()

        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[408, 429, 500, 502, 503, 504],
            allowed_methods=frozenset(['GET', 'POST']),
            raise_on_status=False
        )

        adapter = HTTPAdapter(
            pool_connections=self.pool_connections,
            pool_maxsize=self.pool_maxsize,
            max_retries=retry_strategy
        )

        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def sort_links(self) -> dict[str, str]:
        """Sort segment links numerically by their keys."""
        return dict(sorted(self.segment_links.items(), key=lambda item: int(item[0])))

    def _download_segment(self, url: str, filename: Path) -> bool:
        """Download a single video segment with retry logic."""
        try:
            with self.session.get(url, stream=True, timeout=self.timeout) as response:
                response.raise_for_status()
                with filename.open('wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:  # filter out keep-alive chunks
                            f.write(chunk)
            return True
        except requests.RequestException as e:
            print(f"Error downloading {url}: {e!r}")
            return False

    def _download_segment_with_retry(self, url: str, filename: Path) -> bool:
        """Download a segment with retry logic and progress reporting"""
        for attempt in range(self.max_retries + 1):
            try:
                if self._download_segment(url, filename):
                    return True

                if attempt < self.max_retries:
                    logging.info(f"Retrying segment {filename.name} (attempt {attempt + 1}/{self.max_retries})")

            except Exception as e:
                if attempt >= self.max_retries:
                    logging.info(
                        f"Failed to download segment {filename.name} after {self.max_retries} retries: {str(e)}"
                    )
        return False

    def download_all_segments(self, meta: Optional[Dict[str, Any]]) -> List[Path]:
        """Download all segments in parallel using optimized connection pool"""
        sorted_links = self.sort_links()

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Create all target filenames first
            segment_files = [
                self.temp_dir / f'segment_{str(idx).zfill(4)}.ts'
                for idx in sorted_links.keys()
            ]

            # Download with retry for all segments
            download_func = partial(self._download_segment_with_retry)
            results = []

            for i, result in tqdm(
                    enumerate(executor.map(download_func, sorted_links.values(), segment_files)),
                    total=len(segment_files)
            ):
                if meta is not None:
                    progress: ttk.Progressbar = meta.get("progress")
                    progress["value"] = (i + 1) / len(segment_files) * 100
                    root: tk.Tk = meta.get("root")
                    root.update_idletasks()

                results.append(result)

        successful_files = [f for f, success in zip(segment_files, results) if success]
        success_count = len(successful_files)
        total_count = len(segment_files)

        if success_count != total_count:
            logging.info("Only downloaded %s segments successfully", success_count / total_count)

        logging.info(
            "Download results: %s succeeded, %s failed",
            success_count,
            total_count - success_count
        )
        return successful_files

    def combine_segments(self, segment_files: list[Path], output_filename: str = 'combined_video.ts') -> Path:
        """Combine all downloaded segments into one video file."""
        output_path = self.save_dir / output_filename

        logging.info(f"Combining %s segments into %s", len(segment_files), output_path)

        with output_path.open('wb') as outfile:
            for segment_file in tqdm(sorted(segment_files), desc="Combining ts files into one video"):
                with segment_file.open('rb') as infile:
                    outfile.write(infile.read())

        return output_path

    def cleanup_temp_files(self, segment_files: list[Path]) -> None:
        """Remove temporary segment files."""
        for segment_file in segment_files:
            try:
                segment_file.unlink(missing_ok=True)
            except OSError as e:
                logging.info(f"Warning: Could not delete {segment_file}: {e}")

    def process(
            self,
            output_filename: str = 'combined_video.ts',
            cleanup: bool = True,
            output_format: Literal['ts', 'mp4'] = 'ts',
            meta: Optional[Dict[str, Any]] = None
    ) -> Path:
        if output_format not in ('ts', 'mp4'):
            raise ValueError("output_format must be either 'ts' or 'mp4'")

        if not output_filename.endswith(output_format):
            output_filename = f"{output_filename.rsplit('.', 1)[0]}.{output_format}"

        segment_files = self.download_all_segments(meta=meta)

        if not segment_files:
            raise RuntimeError("No segments were successfully downloaded")

        final_path = self.combine_segments(segment_files, output_filename)

        if cleanup:
            self.cleanup_temp_files(segment_files)

        print(f"Successfully created video at: {final_path}")
        return final_path

    def __enter__(self) -> "VideoSegmentGluer":
        """Context manager entry point."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit point - ensures session is closed."""
        self.session.close()

    def close(self) -> None:
        """Explicit cleanup method."""
        self.session.close()

    def __del__(self) -> None:
        """Destructor - ensures session is closed."""
        self.close()


async def get_index_link() -> str:
    async with VideoIndexCapturer() as capturer:
        index_link: str = await capturer.get_index_url()

    return index_link


def parse_m3u8_file(index_url: str) -> Dict[str, str]:
    resp = requests.get(url=index_url)
    parsed_ts_urls: List[str] = [href for href in resp.text.split("\n") if href.startswith("https://")]
    logging.info("Captured %s fragments", len(parsed_ts_urls))
    return {str(i): href for i, href in enumerate(parsed_ts_urls)}


def download_ui(save_dir: Path, output_filename: str, meta: Dict[str, Any]) -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    index_url: str = loop.run_until_complete(get_index_link())
    hrefs: Dict[str, str] = parse_m3u8_file(index_url=index_url)
    gluer: VideoSegmentGluer = VideoSegmentGluer(
        segment_links=hrefs, save_dir=save_dir
    )
    gluer.process(output_filename=output_filename, cleanup=True, meta=meta)


class VideoSnifferApp:
    def __init__(self, root: tk.Tk):
        self.root: tk.Tk = root
        self.root.title("VideoSniffer")
        self.root.geometry("400x350")
        self.selected_folder = Path()
        self.create_widgets()

    def create_widgets(self):
        """Add all widgets to the main window."""
        tk.Label(self.root, text="VideoSniffer", font=("Arial", 18)).pack(pady=10)

        self.folder_label: tk.Label = tk.Label(self.root, text="No folder selected", font=("Arial", 10), fg="grey")
        self.folder_label.pack(pady=5)

        select_button: tk.Button = tk.Button(self.root, text="Select Folder", command=self.select_folder)
        select_button.pack(pady=5)

        tk.Label(self.root, text="Filename:", font=("Arial", 10)).pack(pady=(10, 0))
        self.filename_entry: tk.Entry = tk.Entry(self.root, font=("Arial", 12), width=30)
        self.filename_entry.pack(pady=5)

        download_button: tk.Button = tk.Button(
            self.root, text="SEARCH MOVIES", font=("Arial", 14), width=20, height=2,
            command=self.initiate_download
        )
        download_button.pack(pady=20)

        self.progress: ttk.Progressbar = ttk.Progressbar(self.root, length=300, mode='determinate')
        self.progress.pack(pady=10)

    def select_folder(self) -> None:
        """Opens prompt to select folder"""
        save_dir: str = filedialog.askdirectory()
        if save_dir:
            self.selected_folder = Path(save_dir)
            self.folder_label.config(text=f"Folder: {save_dir}")

    def initiate_download(self) -> None:
        filename = self.filename_entry.get().strip()

        if not self.selected_folder:
            messagebox.showerror("Error", "Please select a folder first.")
            return
        if not filename:
            messagebox.showerror("Error", "Please enter a filename.")
            return

        # Run run_download in its own thread not to block main UI
        threading.Thread(
            target=self.run_download,
            args=(self.selected_folder, f"{filename}.ts"),
            daemon=True
        ).start()

    def run_download(self, save_dir: Path, output_filename: str) -> None:
        self.progress['value'] = 0
        download_ui(
            save_dir=save_dir,
            output_filename=output_filename,
            meta={"progress": self.progress, "root": self.root}
        )
        messagebox.showinfo("Success", f"Download completed for {output_filename}")


def main():
    root = tk.Tk()
    app = VideoSnifferApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
