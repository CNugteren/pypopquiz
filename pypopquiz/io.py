"""I/O utilities, including disk and Youtube I/O"""

import json
from pathlib import Path
from typing import Dict

from pytube import YouTube


ROOT_KEYS = ["round", "theme", "questions"]
QUESTION_KEYS = ["artist", "title", "video", "question", "answer"]
VIDEO_KEYS = ["source", "url", "format"]
Q_AND_A_KEYS = ["interval", "video", "audio"]


def log(message: str) -> None:
    """Prints a log message to screen"""
    print("[PPQ] " + message)


def verify_input(input_data: Dict) -> None:
    """Verifies that the input JSON is valid. If not, raises an error indicating the mistake"""

    for root_key in ROOT_KEYS:
        if root_key not in input_data.keys():
            raise KeyError("Missing key '{:s}' from input JSON".format(root_key))

    for index, question in enumerate(input_data["questions"]):
        for q_key in QUESTION_KEYS:
            if q_key not in question.keys():
                raise KeyError("Missing key '{:s}' from question's {:d} input JSON".format(q_key, index))
        for v_key in VIDEO_KEYS:
            if v_key not in question["video"].keys():
                raise KeyError("Missing key '{:s}' from question's {:d} video input JSON".format(v_key, index))
        for q_and_a in ["question", "answer"]:
            for key in Q_AND_A_KEYS:
                if key not in question[q_and_a].keys():
                    raise KeyError("Missing key '{:s}' from question {:d}'s {:s} section JSON".format(key, index,
                                                                                                      q_and_a))


def read_input(file_name: Path) -> Dict:
    """Reads and validates a popquiz input JSON file"""
    with file_name.open() as json_data:
        input_data = json.load(json_data)
        verify_input(input_data)
        return input_data


def get_video_file_name(video_data: Dict[str, str]) -> Path:
    """Constructs the name of the video file on disk"""
    return Path(video_data["url"] + "." + video_data["format"])


def get_video(video_data: Dict[str, str], output_dir: Path) -> None:
    """Downloads a video to a local output directory, skips if already there"""

    if not output_dir.exists():
        output_dir.mkdir()

    video_source = video_data["source"]
    video_id = video_data["url"]

    output_file = output_dir / get_video_file_name(video_data)
    if output_file.exists():
        log("Skipping downloading of video '{:s}', already on disk".format(video_id))
        return

    if video_source == "youtube":
        log("Downloading video '{:s}' from Youtube...".format(video_id))
        video = YouTube("https://www.youtube.com/watch?v={:s}".format(video_id))
        video = video.streams.filter(subtype=video_data["format"]).first()
        video.download(output_path=str(output_dir), filename=video_id)

    else:
        raise KeyError("Unsupported source(s) '{:s}'".format(video_source))
