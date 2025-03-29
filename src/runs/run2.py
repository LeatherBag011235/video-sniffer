import sys 
sys.path.append(r"C:\Users\Maxim Shibanov\Projects_Py\video-sniffer\src")

from pathlib import Path
from sniffer_class.video_segment_gluer import VideoSegmentGluer

if __name__ == "__main__":
    segments_dict = {
        '0': 'https://cdn4574.entouaedon.com/vod/6c42e30839a5c911e28b52840fbe72f4/360/segment0.ts?md5=4W0sQ0U7rUNcpxDhb82K-Q&expires=1743263873',
        '359': 'https://cdn4574.entouaedon.com/vod/6c42e30839a5c911e28b52840fbe72f4/720/segment359.ts?md5=OKBHIGGau1cc1-IED-s5uQ&expires=1743263883'
    }

    gluer = VideoSegmentGluer(
        segment_links=segments_dict,
        #save_dir=Path('C:/Video_Sniffer/saved_videos/movie_title')
    )
    
    try:
        final_video_path = gluer.process(
            output_filename='full_movie.ts',
            cleanup=True
        )

    except Exception as e:
        print(f"Error processing video: {e}")