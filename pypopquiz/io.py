"""I/O utilities, including disk and Youtube I/O"""

import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import jsonschema
from pytube import YouTube


def log(message: str) -> None:
    """Prints a log message to screen"""
    print("[PPQ] " + message)


def get_interval_in_s(interval: Tuple[str, str]) -> Tuple[int, int]:
    """Converts an interval in string form (e.g. [1:10, 2:30] in seconds, e.g. [70, 150] seconds"""
    return (int(interval[0].split(":")[0]) * 60 + int(interval[0].split(":")[1]),
            int(interval[1].split(":")[0]) * 60 + int(interval[1].split(":")[1]))


def get_interval_duration(interval: Tuple[str, str]) -> int:
    """Converts an interval in string form (e.g. [1:10, 2:30] to duration, e.g. 80 seconds"""
    interval_s = get_interval_in_s(interval)
    return interval_s[1] - interval_s[0]


def verify_input(input_data: Dict) -> None:
    """Verifies that the input JSON is valid. If not, raises an error indicating the mistake"""

    schema = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "required": ["round", "theme", "questions"],
        "additionalProperties": False,
        "properties": {
            "round": {"type": "number"},
            "theme": {"type": "string"},
            "spacers": {"type": "boolean"},
            "use_cached_video_files": {"type": "boolean"},
            "background_image": {"type": "string"},
            "first_question_is_example": {"type": "boolean"},
            "questions": {
                "type": "array",
                "minItems": 1,
                "additionalProperties": False,
                "items": {
                    "type": "object",
                    "required": ["sources", "question_video", "question_audio",
                                 "answer_video", "answer_audio", "answers"],
                    "properties": {
                        "sources": {
                            "type": "array",
                            "minItems": 1,
                            "additionalProperties": False,
                            "items": {
                                "type": "object",
                                "required": ["source", "url", "format"],
                                "properties": {
                                    "source": {"type": "string"},
                                    "url": {"type": "string"},
                                    "format": {"type": "string"},
                                }
                            }
                        },
                        "question_video": {
                            "type": "array",
                            "minItems": 1,
                            "additionalProperties": False,
                            "items": {
                                "type": "object",
                                "required": ["source", "interval"],
                                "additionalProperties": True,
                                "properties": {
                                    "source": {"type": "number"},
                                    "interval": {"type": "array"},
                                    "repetitions": {"type": "number"},
                                }
                            }
                        },
                        "question_audio": {
                            "type": "array",
                            "minItems": 1,
                            "additionalProperties": False,
                            "items": {
                                "type": "object",
                                "required": ["source", "interval"],
                                "additionalProperties": True,
                                "properties": {
                                    "source": {"type": "number"},
                                    "interval": {"type": "array"},
                                    "repetitions": {"type": "number"},
                                }
                            }
                        },
                        "answer_video": {
                            "type": "array",
                            "minItems": 1,
                            "additionalProperties": False,
                            "items": {
                                "type": "object",
                                "required": ["source", "interval"],
                                "additionalProperties": True,
                                "properties": {
                                    "source": {"type": "number"},
                                    "interval": {"type": "array"},
                                    "repetitions": {"type": "number"},
                                }
                            }
                        },
                        "answer_audio": {
                            "type": "array",
                            "minItems": 1,
                            "additionalProperties": False,
                            "items": {
                                "type": "object",
                                "required": ["source", "interval"],
                                "additionalProperties": True,
                                "properties": {
                                    "source": {"type": "number"},
                                    "interval": {"type": "array"},
                                    "repetitions": {"type": "number"},
                                }
                            }
                        },
                        "answers": {
                            "type": "array",
                            "minItems": 1,
                            "additionalProperties": False,
                            "items": {
                                "type": "object",
                                "additionalProperties": True,
                            }
                        }
                    }
                }
            }
        }
    }
    jsonschema.validate(input_data, schema)
    for question in input_data["questions"]:
        if len(question["answers"]) != len(question["answer_video"]):
            raise ValueError("Expected {:d} answers, got {:d}".
                             format(len(question["answer_video"]), len(question["answers"])))
        question_video_time = sum((get_interval_duration(item["interval"]) for item in question["question_video"]))
        question_audio_time = sum((get_interval_duration(item["interval"]) for item in question["question_audio"]))
        if question_video_time != question_audio_time:
            raise ValueError("Mismatching question audio ({:d}s) and video ({:d}s) runtime".
                             format(question_audio_time, question_video_time))
        answer_video_time = sum((get_interval_duration(item["interval"]) for item in question["answer_video"]))
        answer_audio_time = sum((get_interval_duration(item["interval"]) for item in question["answer_audio"]))
        if answer_video_time != answer_audio_time:
            raise ValueError("Mismatching answer audio ({:d}s) and video ({:d}s) runtime".
                             format(answer_audio_time, answer_video_time))


def read_input(file_name: Path) -> Dict:
    """Reads and validates a popquiz input JSON file"""
    with file_name.open() as json_data:
        input_data = json.load(json_data)
        verify_input(input_data)
        return input_data


def write_lines(text: Iterable[str], file_name: Path) -> None:
    """Writes a list of items to file"""
    file_name.write_text("\n".join(text)+"\n")


def get_video_file_name(video_data: Dict[str, str]) -> Path:
    """Constructs the name of the video file on disk"""
    return Path(video_data["url"] + "." + video_data["format"])


def get_video(video_data: Dict[str, str], output_dir: Path, input_dir: Path) -> None:
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
    elif video_source == "local":
        input_file = input_dir / get_video_file_name(video_data)
        input_file.rename(output_file)
    else:
        raise KeyError("Unsupported source(s) '{:s}'".format(video_source))
