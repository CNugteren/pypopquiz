"""I/O utilities, including disk and JSON parsing"""

import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import jsonschema

import pypopquiz as ppq
import pypopquiz.iovarsubs

SOURCES_BASE_FOLDER = "sources"


def log(message: str) -> None:
    """Prints a log message to screen"""
    print("[PPQ] " + message)


def get_interval_in_s(interval: Tuple[str, str]) -> Tuple[int, int]:
    """Converts an interval in string form (e.g. [1:10, 2:30] in seconds, e.g. [70, 150] seconds"""
    return (int(interval[0].split(":")[0]) * 60 + int(interval[0].split(":")[1][:2]),
            int(interval[1].split(":")[0]) * 60 + int(interval[1].split(":")[1][:2]))


def get_interval_in_fractional_s(interval: Tuple[str, str]) -> Tuple[float, float]:
    """Converts an interval in string form (e.g. [1:10, 2:30] in seconds, e.g. [70, 150] seconds"""
    seconds = get_interval_in_s(interval)
    out = [float(s) for s in seconds]
    for part in (0, 1):
        fsec = interval[part].split('.')
        out[part] = float(seconds[part])
        if len(fsec) == 2:
            out[part] += float('0.' + fsec[1])

    return (out[0], out[1])


def get_interval_duration(interval: Tuple[str, str]) -> int:
    """Converts an interval in string form (e.g. [1:10, 2:30] to duration, e.g. 80 seconds"""
    interval_s = get_interval_in_s(interval)
    return interval_s[1] - interval_s[0]


def total_duration(clips: List[Dict]) -> int:
    """Calculate the total duration of a list of clip specifications."""
    return sum((get_interval_duration(item["interval"]) for item in clips))


def verify_input(input_data: Dict) -> None:
    """Verifies that the input JSON is valid. If not, raises an error indicating the mistake"""
    # pylint: disable=too-many-branches

    schema = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "required": ["round", "theme", "questions", "questioned"],
        "additionalProperties": False,
        "properties": {
            "round": {"type": "number"},
            "theme": {"type": "string"},
            "spacers": {"type": "string"},
            "use_cached_video_files": {"type": "boolean"},
            "background_image": {"type": "string"},
            "first_question_is_example": {"type": "boolean"},
            "questioned": {
                "type": "array",
                "minItems": 1,
                "additionalProperties": False,
                "items": {
                    "type": "string",
                }
            },
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
                                "required": ["source", "identifier"],
                                "properties": {
                                    "source": {"type": "string"},
                                    "identifier": {"type": "string"},
                                    "format": {"type": "string"},
                                    "text": {"type": "array", "minItems": 1, "items": {"type": "string"}},
                                    "duration": {"type": "integer"},
                                }
                            }
                        },
                        "question_video": {
                            "type": "array",
                            "minItems": 1,
                            "additionalProperties": False,
                            "items": {
                                "type": "object",
                                "required": ["source"],
                                "additionalProperties": True,
                                "properties": {
                                    "source": {"type": "number"},
                                    "interval": {"type": "array"},
                                    "reverse": {"type": "boolean"}
                                }
                            }
                        },
                        "question_audio": {
                            "type": "array",
                            "minItems": 1,
                            "additionalProperties": False,
                            "items": {
                                "type": "object",
                                "required": ["source"],
                                "additionalProperties": True,
                                "properties": {
                                    "source": {"type": "number"},
                                    "interval": {"type": "array"},
                                    "reverse": {"type": "boolean"},
                                    "beeps_events": {"type": "string"}
                                }
                            }
                        },
                        "repetitions": {"type": "number"},
                        "answer_video": {
                            "type": "array",
                            "minItems": 1,
                            "additionalProperties": False,
                            "items": {
                                "type": "object",
                                "required": ["source"],
                                "additionalProperties": True,
                                "properties": {
                                    "source": {"type": "number"},
                                    "interval": {"type": "array"},
                                    "reverse": {"type": "boolean"},
                                    "answer_label_events": {"type": "string"}
                                }
                            }
                        },
                        "answer_audio": {
                            "type": "array",
                            "minItems": 1,
                            "additionalProperties": False,
                            "items": {
                                "type": "object",
                                "required": ["source"],
                                "additionalProperties": True,
                                "properties": {
                                    "source": {"type": "number"},
                                    "interval": {"type": "array"},
                                    "reverse": {"type": "boolean"}
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
                        },
                        "variables": {
                            "type": "object"
                        }
                    }
                }
            }
        }
    }
    jsonschema.validate(input_data, schema)
    ppq.iovarsubs.substitute_variables(input_data)

    # Sets intervals to the full duration if not specified
    for index, question in enumerate(input_data["questions"]):
        for sub_type in ("question_video", "question_audio", "answer_video", "answer_audio"):
            for sub_item in question[sub_type]:
                source_index = sub_item["source"]
                if "interval" not in sub_item.keys():
                    source = question["sources"][source_index]
                    if "duration" not in source.keys():
                        raise ValueError("Missing interval for question {:d}'s '{:s}'".format(index, sub_type))
                    else:
                        minutes = source["duration"] // 60
                        seconds = source["duration"] % 60
                        sub_item["interval"] = ["0:00", "{:d}:{:2d}".format(minutes, seconds)]
                        log("Set duration for question {:d}'s '{:s}' to {:s}".
                            format(index, sub_type, str(sub_item["interval"])))

    # Additional constraints on the input
    for question in input_data["questions"]:
        for source in question["sources"]:
            source_keys = source.keys() - {"source", "identifier"}
            if source["source"] == "youtube":
                if source_keys != {"format"}:
                    raise ValueError("Missing source keys from Youtube source {:s}".format(str(source)))
            elif source["source"] == "text":
                if source_keys != {"text", "duration"}:
                    raise ValueError("Missing source keys from text source {:s}".format(str(source)))
                source["format"] = "mp4"  # default format
            elif source["source"] == "image":
                if source_keys != {"duration"}:
                    raise ValueError("Missing source keys from image source {:s}".format(str(source)))
                source["format"] = "mp4"  # default format
        if len(question["answers"]) != len(question["answer_video"]):
            raise ValueError("Expected {:d} answers, got {:d}".
                             format(len(question["answer_video"]), len(question["answers"])))
        question_video_time = total_duration(question["question_video"])
        question_audio_time = total_duration(question["question_audio"])
        if question_video_time != question_audio_time:
            raise ValueError("Mismatching question audio ({:d}s) and video ({:d}s) runtime".
                             format(question_audio_time, question_video_time))
        answer_video_time = total_duration(question["answer_video"])
        answer_audio_time = total_duration(question["answer_audio"])
        if answer_video_time != answer_audio_time:
            raise ValueError("Mismatching answer audio ({:d}s) and video ({:d}s) runtime".
                             format(answer_audio_time, answer_video_time))
        answer_keys = sorted([item for answer_dict in question["answers"] for item in answer_dict.keys()])
        questioned = sorted(input_data["questioned"])
        if answer_keys != questioned:
            raise ValueError("Mismatching answer keys given under 'answered' and 'questioned', they should match")


def read_input(file_name: Path) -> Dict:
    """Reads and validates a popquiz input JSON file"""
    with file_name.open() as json_data:
        input_data = json.load(json_data)
        verify_input(input_data)
        return input_data


def write_lines(text: Iterable[str], file_name: Path) -> None:
    """Writes a list of items to file"""
    file_name.write_text("\n".join(text)+"\n")


def get_source_file_name(source_data: Dict[str, str]) -> Path:
    """Constructs the name of the source file on disk"""
    duration = "_{:d}".format(source_data["duration"]) if "duration" in source_data else ""
    return Path(SOURCES_BASE_FOLDER) / Path(source_data["identifier"] + duration + "." + source_data["format"])
