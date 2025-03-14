import sys 
sys.path.append(r"C:\Users\Maxim Shibanov\Projects_Py\video-sniffer\src")

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
import yt_dlp
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Initialize FastAPI
app = FastAPI(
    title="Video Sniffer API",
    description="An API for extracting and downloading videos from webpages, including JavaScript-heavy sites.",
    version="1.0.0"
)

class VideoSniffer(BaseModel):
    """Request model for passing video URL."""
    url: str

def fetch_page_with_selenium(url: str) -> str:
    """
    Fetches full HTML content using Selenium to handle JavaScript-rendered pages.
    
    Args:
        url (str): The webpage URL to fetch.

    Returns:
        str: The HTML content of the page.
    """
    options = Options()
    options.add_argument("--headless")  # Run in headless mode (no browser window)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)

    # Wait a few seconds to allow lazy-loaded content to appear
    driver.implicitly_wait(5)  # Adjust wait time if needed

    page_source = driver.page_source
    driver.quit()
    return page_source

def extract_video_url(page_url: str) -> str:
    """
    Extracts a video URL from a given webpage.

    Uses Selenium to fetch the full page and BeautifulSoup to parse the HTML.

    Args:
        page_url (str): The URL of the webpage containing the video.

    Returns:
        str: The direct URL of the video if found, otherwise None.

    Raises:
        HTTPException: If an error occurs during extraction.
    """
    try:
        # Fetch the page source using Selenium
        page_html = fetch_page_with_selenium(page_url)
        soup = BeautifulSoup(page_html, "html.parser")

        # Look for a <video> tag
        video_tag = soup.find("video")
        if video_tag and video_tag.find("source"):
            return video_tag.find("source")["src"]

        # Alternative: Check if the video is embedded in an <iframe>
        iframe = soup.find("iframe")
        if iframe:
            return iframe["src"]  # Might need further parsing for streaming sites

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting video URL: {str(e)}")

    return None  # Return None if no video is found

def download_video(video_url: str, output_path: str = "downloaded_video.mp4") -> str:
    """
    Downloads a video from a direct URL using yt-dlp.

    Args:
        video_url (str): The direct URL of the video.
        output_path (str): The filename to save the video as (default: 'downloaded_video.mp4').

    Returns:
        str: The saved file path.
    
    Raises:
        HTTPException: If download fails.
    """
    ydl_opts = {
        "outtmpl": output_path,
        "quiet": True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        return output_path
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@app.post("/download_video/", summary="Download Video", tags=["Video"])
def download_video_api(request: VideoSniffer):
    """
    API endpoint to extract and download a video from a given webpage.

    Args:
        request (VideoSniffer): JSON body containing the webpage URL.

    Returns:
        dict: A JSON response indicating success or failure.
    
    Raises:
        HTTPException: If no video is found or an error occurs.
    """
    try:
        # Extract video URL from the webpage
        video_url = extract_video_url(request.url)
        if not video_url:
            raise HTTPException(status_code=404, detail="No video found on the webpage")

        # Download the video
        output_file = "downloaded_video.mp4"
        download_video(video_url, output_file)

        return {
            "message": "Video downloaded successfully",
            "file_path": output_file
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
