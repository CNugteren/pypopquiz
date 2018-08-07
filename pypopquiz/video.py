"""Module with all video/ffmpeg related functions"""

from pathlib import Path
from typing import Dict, Tuple, List, Any

import ffmpeg

import pypopquiz as ppq
import pypopquiz.io

Stream = Any  # Should actually be "ffmpeg.nodes.FilterableStream" but doesn't work
OutStream = Any  # ffmpeg.nodes.OutputNode


def get_interval_in_s(interval: List[str]) -> List[int]:
    """Converts an interval in string form (e.g. [1:10, 2:30] in seconds, e.g. [70, 150] seconds"""
    return [int(sec.split(":")[0]) * 60 + int(sec.split(":")[1]) for sec in interval]


def repeat_stream(stream_v: Stream, stream_a: Stream) -> Tuple[Stream, Stream]:
    """Concatenates a video and audio stream with itself to make a twice as long video"""
    stream_v = stream_v.split()
    stream_a = stream_a.asplit()
    joined = ffmpeg.concat(stream_v[0].filter("fifo"), stream_a[0].filter("afifo"),
                           stream_v[1].filter("fifo"), stream_a[1].filter("afifo"), v=1, a=1).node
    return joined[0], joined[1]


def fade_in_and_out(stream: Stream, fade_amount_s: int, length_s: int, is_audio: bool) -> Stream:
    """Adds a fade-in and fade-out to/from black for either audio or a video stream"""
    filter_name = "afade" if is_audio else "fade"
    stream = stream.filter(filter_name, type="in", start_time=0, duration=fade_amount_s)
    return stream.filter(filter_name, type="out", start_time=length_s - fade_amount_s, duration=fade_amount_s)


def draw_text_in_box(stream_v: Stream, video_text: str, length: int, width: int, height: int,
                     box_height: int, move: bool, top: bool) -> Stream:
    """Draws a semi-transparent box either at the top or bottom and writes text in it, optionally scrolling by"""
    y_location = 0 if top else height - box_height
    stream_v = stream_v.drawbox(x=0, y=y_location, width=width, height=box_height,
                                color="gray@0.5", thickness="max")  # 'max' == 'fill' in newer versions of ffmpeg
    x_location_text = "{:d} * t / {:d}".format(width, length) if move else "{:d} - text_w / 2".format(width // 2)
    y_location_text = int(box_height * 1/4) if top else int(height - box_height * 3/4)
    stream_v = stream_v.drawtext(text=video_text, fontcolor="white", fontsize=50,
                                 x=x_location_text, y=y_location_text)
    return stream_v


def filter_stream(stream: Stream, kind: str, round_id: int, question: Dict, question_id: int,
                  width: int, height: int, repetitions: int,
                  box_height: int = 100, fade_amount_s: int = 3) -> Tuple[Stream, Stream]:
    """Adds ffmpeg filters to the stream, producing a separate video and audio stream as a result"""

    interval = get_interval_in_s(question[kind]["interval"])
    if interval[1] <= interval[0]:
        raise ValueError("Invalid interval: {:s}".format(str(interval)))
    length_s = interval[1] - interval[0]
    question_text = "Question {:d}.{:d}".format(round_id, question_id)
    answer_text = "{:s} - {:s}".format(question["artist"], question["title"])

    # Video stream
    stream_v = stream["v"]
    stream_v = stream_v.trim(start=interval[0], end=interval[1]).filter("setpts", "PTS-STARTPTS")
    stream_v = fade_in_and_out(stream_v, fade_amount_s, length_s, is_audio=False)
    stream_v = stream_v.filter("scale", width=width, height=height, force_original_aspect_ratio=1)
    stream_v = stream_v.filter("pad", width=width, height=height, x="(ow-iw)/2", y="(oh-ih)/2", color="black")
    stream_v = draw_text_in_box(stream_v, question_text, length_s, width, height, box_height, move=True, top=False)
    if kind == "answer":
        stream_v = draw_text_in_box(stream_v, answer_text, length_s, width, height, box_height, move=False, top=True)

    # Audio stream
    stream_a = stream["a"]
    stream_a = stream_a.filter("atrim", start=interval[0], end=interval[1]).filter("asetpts", "PTS-STARTPTS")
    stream_a = fade_in_and_out(stream_a, fade_amount_s, length_s, is_audio=True)

    if repetitions == 1:
        pass  # no-op
    elif repetitions % 2 == 0:
        for _ in range(repetitions // 2):
            stream_v, stream_a = repeat_stream(stream_v, stream_a)
    else:
        raise RuntimeError("Repetition not 1 or multiple 2, got: {:d}".format(repetitions))

    return stream_v, stream_a


def run_ffmpeg(output_stream: OutStream, display_graph: bool = False) -> None:
    """Runs the ffmpeg command to create the video, applying all the filters"""
    if display_graph:
        output_stream.view(filename="ffmpeg_graph")  # optional visualisation of the graph
    ppq.io.log("Running ffmpeg...")
    ppq.io.log("")
    output_stream.run()
    ppq.io.log("")
    ppq.io.log("Completed ffmpeg, successfully generated result")


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

    stream = ffmpeg.input(str(video_file))
    stream_v, stream_a = filter_stream(stream, kind, round_id, question, question_id, width, height, repetitions)
    output = ffmpeg.output(stream_v, stream_a, str(file_name))
    run_ffmpeg(output)

    return file_name
