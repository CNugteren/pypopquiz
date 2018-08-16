"""Module with all video related functions, using one of the video backends"""

from pathlib import Path
from typing import Dict, List

import pypopquiz as ppq
import pypopquiz.io
import pypopquiz.backends.backend
import pypopquiz.backends.ffmpeg
import pypopquiz.backends.moviepy

VideoBackend = pypopquiz.backends.backend.Backend



def get_interval_in_s(interval: List[str]) -> List[int]:
    """Converts an interval in string form (e.g. [1:10, 2:30] in seconds, e.g. [70, 150] seconds"""
    return [int(sec.split(":")[0]) * 60 + int(sec.split(":")[1]) for sec in interval]


def filter_stream(stream: VideoBackend, kind: str, round_id: int, question: Dict, question_id: int,
                  width: int, height: int, box_height: int = 100, fade_amount_s: int = 3,
                  add_spacer: bool = False) -> VideoBackend:
    """Adds ffmpeg filters to the stream, producing a separate video and audio stream as a result"""

    repetitions = question[kind].get("repetitions", 1)
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

    if add_spacer and kind == "question":
        stream.add_spacer("Get Ready...", duration_s=2)

    return stream


def create_video(kind: str, round_id: int, question: Dict, question_id: int, output_dir: Path,
                 width: int = 1280, height: int = 720, backend: str = 'ffmpeg', add_spacer: bool = False) -> Path:
    """Creates a video for one question, either a question or an answer video"""
    assert kind in ["question", "answer"]

    sources = question["sources"]
    source_index = question[kind]["source"]
    if source_index >= len(sources):
        raise ValueError("Source index {:d} given, but only {:d} source(s) provided".format(source_index, len(sources)))
    video_data = sources[source_index]
    video_file = output_dir / ppq.io.get_video_file_name(video_data)
    if not video_file.exists():
        raise FileNotFoundError("Video file '{:s}' doesn't exist".format(str(video_file)))

    file_name = output_dir / ("{:02d}_{:02d}_{:s}.{:s}".format(round_id, question_id, kind, video_data["format"]))
    if file_name.exists():
        file_name.unlink()  # deletes a previous version

    if backend == 'ffmpeg':
        be = ppq.backends.ffmpeg.FFMpeg
    else:
        be = ppq.backends.moviepy.Moviepy  # type: ignore

    stream = be(video_file, width=width, height=height)
    stream_f = filter_stream(stream, kind, round_id, question, question_id, width, height, add_spacer=add_spacer)
    stream_f.run(file_name)

    return file_name
