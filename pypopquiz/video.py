"""Module with all video related functions, using one of the video backends"""

from pathlib import Path
from typing import Dict, List

import pypopquiz as ppq
import pypopquiz.io
import pypopquiz.backends.backend
import pypopquiz.backends.ffmpeg

VideoBackend = ppq.backends.ffmpeg.FFMpeg  # select the backend to use


def get_interval_in_s(interval: List[str]) -> List[int]:
    """Converts an interval in string form (e.g. [1:10, 2:30] in seconds, e.g. [70, 150] seconds"""
    return [int(sec.split(":")[0]) * 60 + int(sec.split(":")[1]) for sec in interval]


def filter_stream(stream: VideoBackend, kind: str, round_id: int, question: Dict, question_id: int,
                  width: int, height: int, repetitions: int,
                  box_height: int = 100, fade_amount_s: int = 3) -> VideoBackend:
    """Adds ffmpeg filters to the stream, producing a separate video and audio stream as a result"""

    interval = get_interval_in_s(question[kind]["interval"])
    if interval[1] <= interval[0]:
        raise ValueError("Invalid interval: {:s}".format(str(interval)))
    length_s = interval[1] - interval[0]
    question_text = "Question {:d}.{:d}".format(round_id, question_id)
    answer_text = "{:s} - {:s}".format(question["artist"], question["title"])

    stream.trim(start_s=interval[0], end_s=interval[1])
    stream.fade_in_and_out(fade_amount_s, length_s)
    stream.scale_video(width, height)
    stream.draw_text_in_box(question_text, length_s, width, height, box_height, move=True, top=False)
    if kind == "answer":
        stream.draw_text_in_box(answer_text, length_s, width, height, box_height, move=False, top=True)

    if repetitions == 1:
        pass  # no-op
    elif repetitions % 2 == 0:
        for _ in range(repetitions // 2):
            stream.repeat()
    else:
        raise RuntimeError("Repetition not 1 or multiple 2, got: {:d}".format(repetitions))

    return stream


def create_video(kind: str, round_id: int, question: Dict, question_id: int, output_dir: Path,
                 repetitions: int, width: int = 1280, height: int = 720) -> Path:
    """Creates a video for one question, either a question or an answer video"""
    assert kind in ["question", "answer"]

    video_data = question["video"]
    video_file = output_dir / ppq.io.get_video_file_name(video_data)
    if not video_file.exists():
        raise FileNotFoundError("Video file '{:s}' doesn't exist".format(str(video_file)))

    file_name = output_dir / ("{:02d}_{:02d}_{:s}.{:s}".format(round_id, question_id, kind, video_data["format"]))
    if file_name.exists():
        file_name.unlink()  # deletes a previous version

    stream = VideoBackend(video_file)  # currently hard-coded since FFMpeg is the only back-end
    stream = filter_stream(stream, kind, round_id, question, question_id, width, height, repetitions)
    stream.run(file_name)

    return file_name
