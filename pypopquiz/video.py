"""Module with all video related functions, using one of the video backends"""

from pathlib import Path
from typing import Dict, List

import pypopquiz as ppq
import pypopquiz.io
import pypopquiz.backends.backend
import pypopquiz.backends.ffmpeg
import pypopquiz.backends.moviepy

VideoBackend = ppq.backends.backend.Backend


def get_interval_in_s(interval: List[str]) -> List[int]:
    """Converts an interval in string form (e.g. [1:10, 2:30] in seconds, e.g. [70, 150] seconds"""
    return [int(sec.split(":")[0]) * 60 + int(sec.split(":")[1]) for sec in interval]


def filter_stream(stream: VideoBackend, kind: str, round_id: int, question: Dict, question_id: int,
                  box_height: int = 100, fade_amount_s: int = 3,
                  spacer_txt: str = "", is_example: bool = False) -> VideoBackend:
    """Adds ffmpeg filters to the stream, producing a separate video and audio stream as a result"""

    repetitions = question[kind].get("repetitions", 1)
    interval = get_interval_in_s(question[kind]["interval"])
    if interval[1] <= interval[0]:
        raise ValueError("Invalid interval: {:s}".format(str(interval)))
    length_s = interval[1] - interval[0]

    if is_example:
        question_text = "Example question for round {:d}".format(round_id)
    else:
        question_text = "Question {:d}.{:d}".format(round_id, question_id)
    answer_text = "{:s} - {:s}".format(question["artist"], question["title"])

    stream.trim(start_s=interval[0], end_s=interval[1])
    stream.fade_in_and_out(fade_amount_s, length_s)
    stream.scale_video()
    stream.draw_text_in_box(question_text, length_s, box_height, move=True, top=False)
    if kind == "answer":
        stream.draw_text_in_box(answer_text, length_s, box_height, move=False, top=True)

    if repetitions == 1:
        pass  # no-op
    elif repetitions % 2 == 0:
        for _ in range(repetitions // 2):
            stream.repeat()
    else:
        raise RuntimeError("Repetition not 1 or multiple 2, got: {:d}".format(repetitions))

    if len(spacer_txt) != 0 and kind == "question":
        stream.add_spacer(spacer_txt, duration_s=2)

    return stream


def get_backend(backend: str):
    """Selects the backend based on a string name"""
    if backend == 'ffmpeg':
        return ppq.backends.ffmpeg.FFMpeg
    if backend == 'moviepy':
        return ppq.backends.moviepy.Moviepy  # type: ignore
    raise ValueError('Invalid backend {} selected.'.format(backend))


def get_video_source(question: Dict, kind: str) -> Dict:
    """Returns the dict for the source file for this question or answer."""
    sources = question["sources"]
    source_index = question[kind]["source"]
    if source_index >= len(sources):
        raise ValueError("Source index {:d} given, but only {:d} source(s) provided".format(source_index, len(sources)))
    return sources[source_index]


def create_video(kind: str, round_id: int, question: Dict, question_id: int, output_dir: Path,
                 width: int = 1280, height: int = 720, backend: str = 'ffmpeg', spacer_txt: str = "",
                 use_cached_video_files: bool = False, is_example: bool = False) -> Path:
    """Creates a video for one question, either a question or an answer video"""
    assert kind in ["question", "answer"]

    video_source = get_video_source(question, kind)
    video_file = output_dir / ppq.io.get_video_file_name(video_source)
    if not video_file.exists():
        raise FileNotFoundError("Video file '{:s}' doesn't exist".format(str(video_file)))

    # Force output file to be a video
    target_format = 'mp4'
    file_name = output_dir / ("{:02d}_{:02d}_{:s}.{:s}".format(round_id, question_id, kind, target_format))

    generate_video = True
    if file_name.exists():
        if use_cached_video_files:
            generate_video = False
        else:
            file_name.unlink()  # deletes a previous version

    backend_cls = get_backend(backend)
    stream = backend_cls(video_file, width=width, height=height)
    stream = filter_stream(stream, kind, round_id, question, question_id, spacer_txt=spacer_txt, is_example=is_example)
    file_name_out = stream.run(file_name, dry_run=not generate_video)

    return file_name_out


def combine_videos(video_files: List[Path], kind: str, round_id: int, output_dir: Path,
                   backend: str = 'ffmpeg') -> None:
    """Combines a list of video files together into a single video"""
    backend_cls = get_backend(backend)

    assert video_files  # assumes at least one item
    stream = backend_cls(video_files[0])
    for video_file in video_files[1:]:
        new_stream = backend_cls(video_file)
        stream.combine(new_stream)

    file_name = output_dir / ("{:02d}_{:s}{:s}".format(round_id, kind, video_files[0].suffix))
    stream.run(file_name)
