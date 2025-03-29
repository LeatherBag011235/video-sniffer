from pathlib import Path

from sniffer_class.downloader import download_cli


def main():
    # Select film you want to download and pass index_url to Downloader
    download_cli(
        save_dir=Path(r"D:\HSE\Introduction_Python\project\src\videos"),
        output_filename="movie.ts",
    )


if __name__ == '__main__':
    main()
