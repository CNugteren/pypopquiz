"""Module with all video related functions, using one of the video backends"""

from pathlib import Path
from typing import Dict, List, Tuple

import pypopquiz as ppq
import pypopquiz.io
import pypopquiz.backends.backend
import pypopquiz.backends.ffmpeg
import pypopquiz.backends.moviepy

VideoBackend = ppq.backends.backend.Backend


def repeat_stream(stream: VideoBackend, repetitions: int):
    """Repeats a stream a number of times"""
    if repetitions == 1:
        pass  # no-op
    elif repetitions % 2 == 0:
        for _ in range(repetitions // 2):
            stream.repeat()
    else:
        raise RuntimeError("Repetition not 1 or multiple 2, got: {:d}".format(repetitions))


def filter_stream_video(stream: VideoBackend, kind: str, round_id: int, answer_text: str, question_id: int,
                        repetitions: int, interval: Tuple[int, int], box_height: int = 100, fade_amount_s: int = 3,
                        spacer_txt: str = "", is_example: bool = False) -> VideoBackend:
    """Adds ffmpeg filters to the stream, producing a video stream as a result"""

    if interval[1] <= interval[0]:
        raise ValueError("Invalid interval: {:s}".format(str(interval)))
    length_s = interval[1] - interval[0]

    if is_example:
        question_text = "Example question for round {:d}".format(round_id)
    else:
        question_text = "Question {:d}.{:d}".format(round_id, question_id)

    stream.trim(start_s=interval[0], end_s=interval[1])
    stream.fade_in_and_out(fade_amount_s, length_s)
    stream.scale_video()
    stream.draw_text_in_box(question_text, length_s, box_height, move=True, top=False)
    if kind == "answer":
        stream.draw_text_in_box(answer_text, length_s, box_height, move=False, top=True)
    repeat_stream(stream, repetitions)
    if spacer_txt != "" and kind == "question":
        stream.add_spacer(spacer_txt, duration_s=2)

    return stream


def filter_stream_audio(stream: VideoBackend, kind: str, repetitions: int, interval: Tuple[int, int],
                        fade_amount_s: int = 3, spacer_txt: str = "") -> VideoBackend:
    """Adds ffmpeg filters to the stream, producing an audio stream as a result"""

    if interval[1] <= interval[0]:
        raise ValueError("Invalid interval: {:s}".format(str(interval)))
    length_s = interval[1] - interval[0]

    stream.trim(start_s=interval[0], end_s=interval[1])
    stream.fade_in_and_out(fade_amount_s, length_s)
    repeat_stream(stream, repetitions)
    if spacer_txt != "" and kind == "question":
        stream.add_silence(duration_s=2)  # for the spacer

    return stream


def get_backend(backend: str):
    """Selects the backend based on a string name"""
    if backend == 'ffmpeg':
        return ppq.backends.ffmpeg.FFMpeg
    if backend == 'moviepy':
        return ppq.backends.moviepy.Moviepy  # type: ignore
    raise ValueError('Invalid backend {} selected.'.format(backend))


def get_sources(question: Dict, media: str, kind: str) -> List[Dict]:
    """Returns the dict for the source file for this question or answer."""
    assert media in ["video", "audio"]
    sources = question["sources"]
    source_indices = [sub_question["source"] for sub_question in question[kind + "_" + media]]
    for source_index in source_indices:
        if source_index >= len(sources):
            raise ValueError("Source index {:d} given, but only {:d} source(s) provided".
                             format(source_index, len(sources)))
    return [sources[source_index] for source_index in source_indices]


def create_video(kind: str, round_id: int, question: Dict, question_id: int, output_dir: Path,
                 width: int = 1280, height: int = 720, backend: str = 'ffmpeg', spacer_txt: str = "",
                 use_cached_video_files: bool = False, is_example: bool = False) -> Path:
    """Creates a video for one question, either a question or an answer video"""
    assert kind in ["question", "answer"]

    video_sources = get_sources(question, "video", kind)
    audio_sources = get_sources(question, "audio", kind)
    video_files = [output_dir / ppq.io.get_source_file_name(video_source) for video_source in video_sources]
    audio_files = [output_dir / ppq.io.get_source_file_name(audio_source) for audio_source in audio_sources]
    for media_file in video_files + audio_files:
        if not media_file.exists():
            raise FileNotFoundError("Video/audio file '{:s}' doesn't exist".format(str(media_file)))

    # Force output file to be a video
    target_format = 'mp4'
    file_name = output_dir / ("{:02d}_{:02d}_{:s}.{:s}".format(round_id, question_id, kind, target_format))

    generate_video = True
    if file_name.exists():
        if use_cached_video_files:
            generate_video = False
        else:
            file_name.unlink()  # deletes a previous version

    # TODO: Handle multiple audio and video files in the backends
    media_id = 0
    answer_text = " - ".join(question["answers"][media_id].values())

    # Process the video
    repetitions = question[kind+"_video"][media_id].get("repetitions", 1)
    interval = ppq.io.get_interval_in_s(question[kind+"_video"][media_id]["interval"])
    backend_cls = get_backend(backend)
    stream_video = backend_cls(video_files[media_id], has_video=True, has_audio=False, width=width, height=height)
    stream_video = filter_stream_video(stream_video, kind, round_id, answer_text, question_id, repetitions, interval,
                                       spacer_txt=spacer_txt, is_example=is_example)

    # Process the audio
    repetitions = question[kind + "_audio"][media_id].get("repetitions", 1)
    interval = ppq.io.get_interval_in_s(question[kind + "_audio"][media_id]["interval"])
    backend_cls = get_backend(backend)
    stream_audio = backend_cls(audio_files[media_id], has_video=False, has_audio=True, width=width, height=height)
    stream_audio = filter_stream_audio(stream_audio, kind, repetitions, interval, spacer_txt=spacer_txt)

    # Combine the audio and video
    stream_video.add_audio(stream_audio)
    file_name_out = stream_video.run(file_name, dry_run=not generate_video)

    return file_name_out


def combine_videos(video_files: List[Path], kind: str, round_id: int, output_dir: Path,
                   backend: str = 'ffmpeg') -> None:
    """Combines a list of video files together into a single video"""
    backend_cls = get_backend(backend)

    assert video_files  # assumes at least one item
    stream = backend_cls(video_files[0], has_video=True, has_audio=True)
    for video_file in video_files[1:]:
        new_stream = backend_cls(video_file, has_video=True, has_audio=True)
        stream.combine(new_stream)

    file_name = output_dir / ("{:02d}_{:s}{:s}".format(round_id, kind, video_files[0].suffix))
    stream.run(file_name)
