"""Sources access and generation"""

from pathlib import Path
from typing import Dict, Any

import yt_dlp

import pypopquiz as ppq
import pypopquiz.io
import pypopquiz.video


def to_youtube_url(video_identifier: str) -> str:
    """"Convert video identifier to a youtube url."""
    return "https://www.youtube.com/watch?v={:s}".format(video_identifier)


def download_with_yt_dlp(sources_dir: Path, source_url: str, source_format: str) -> None:
    """Download video from YouTube with yt-dlp."""
    ydl_opts = {
        "format": source_format,
        "outtmpl": str(sources_dir) + '/%(id)s.%(ext)s',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([source_url])


def get_source(source_data: Dict[str, Any], output_dir: Path, input_dir: Path, width: int, height: int,
               backend: str = 'ffmpeg', downloader: str = 'yt-dlp') -> None:
    """Retrieves a source and stores is in a local output directory, skips if already there"""
    if not output_dir.exists():
        output_dir.mkdir()

    sources_dir = output_dir / ppq.io.SOURCES_BASE_FOLDER
    if not sources_dir.exists():
        sources_dir.mkdir()

    source_type = source_data["source"]
    source_url = source_data["identifier"]
    source_format = source_data["format"]

    output_file = output_dir / ppq.io.get_source_file_name(source_data)
    if output_file.exists():
        ppq.io.log("Skipping creation of source '{:s}', already on disk".format(source_url))
        return

    if source_type == "youtube":
        ppq.io.log("Downloading video '{:s}' from Youtube...".format(source_url))

        if downloader == 'yt-dlp':
            download_with_yt_dlp(sources_dir, source_url, source_format)
        else:
            raise ValueError("Invalid downloader selected.")

    elif source_type == "local":
        input_file = input_dir / ppq.io.get_source_file_name(source_data)
        input_file.rename(sources_dir)
    elif source_type == "text":
        ppq.video.create_text_video(output_file, source_data["text"], source_data["duration"],
                                    width=width, height=height, backend=backend)
    elif source_type == "image":
        ppq.video.create_video_from_single_image(output_file, source_data["identifier"], source_data["duration"],
                                                 width=width, height=height, backend=backend)
    else:
        raise KeyError("Unsupported source(s) '{:s}'".format(source_type))
