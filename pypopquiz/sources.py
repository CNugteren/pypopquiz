"""Sources access and generation"""

from pathlib import Path
from typing import Dict, Any

from pytube import YouTube

import pypopquiz as ppq
import pypopquiz.io
import pypopquiz.video


def get_source(source_data: Dict[str, Any], output_dir: Path, input_dir: Path, width: int, height: int) -> None:
    """Retrieves a source and stores is in a local output directory, skips if already there"""

    if not output_dir.exists():
        output_dir.mkdir()
    if not (output_dir / ppq.io.SOURCES_BASE_FOLDER).exists():
        (output_dir / ppq.io.SOURCES_BASE_FOLDER).mkdir()

    source_type = source_data["source"]
    source_url = source_data["identifier"]

    output_file = output_dir / ppq.io.get_source_file_name(source_data)
    if output_file.exists():
        ppq.io.log("Skipping creation of source '{:s}', already on disk".format(source_url))
        return

    if source_type == "youtube":
        ppq.io.log("Downloading video '{:s}' from Youtube...".format(source_url))
        video = YouTube("https://www.youtube.com/watch?v={:s}".format(source_url))
        video = video.streams.filter(subtype=source_data["format"]).first()
        video.download(output_path=str(output_dir / ppq.io.SOURCES_BASE_FOLDER), filename=source_url)
    elif source_type == "local":
        input_file = input_dir / ppq.io.get_source_file_name(source_data)
        input_file.rename(output_dir / ppq.io.SOURCES_BASE_FOLDER)
    elif source_type == "text":
        ppq.video.create_text_video(output_file, source_data["text"], source_data["duration"],
                                    width=width, height=height)
    elif source_type == "image":
        ppq.video.create_video_from_single_image(output_file, source_data["identifier"], source_data["duration"],
                                                 width=width, height=height)
    else:
        raise KeyError("Unsupported source(s) '{:s}'".format(source_type))
