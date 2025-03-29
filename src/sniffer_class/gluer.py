from __future__ import annotations

import logging
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from os import PathLike
from pathlib import Path
from typing import Literal, Dict

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


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

    def download_all_segments(self) -> list[Path]:
        """Download all segments in parallel using optimized connection pool"""
        sorted_links = self.sort_links()

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Create all target filenames first
            segment_files = [
                self.temp_dir / f'segment_{idx.zfill(4)}.ts'
                for idx in sorted_links.keys()
            ]

            # Download with retry for all segments
            download_func = partial(self._download_segment_with_retry)
            results = list(executor.map(
                download_func,
                sorted_links.values(),
                segment_files
            ))

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
            for segment_file in sorted(segment_files):
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
            output_format: Literal['ts', 'mp4'] = 'ts'
    ) -> Path:
        """
        Complete processing pipeline with optimized connection pooling.
        
        Args:
            output_filename: Name for the output file
            cleanup: Whether to remove temporary files
            output_format: Output file format ('ts' or 'mp4')
            
        Returns:
            Path to the final combined video file
        """
        if output_format not in ('ts', 'mp4'):
            raise ValueError("output_format must be either 'ts' or 'mp4'")

        if not output_filename.endswith(output_format):
            output_filename = f"{output_filename.rsplit('.', 1)[0]}.{output_format}"

        segment_files = self.download_all_segments()

        if not segment_files:
            raise RuntimeError("No segments were successfully downloaded")

        final_path = self.combine_segments(segment_files, output_filename)

        if cleanup:
            self.cleanup_temp_files(segment_files)

        print(f"Successfully created video at: {final_path}")
        return final_path

    def __enter__(self) -> VideoSegmentGluer:
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
