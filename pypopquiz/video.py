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


def get_interval_length(interval: Tuple[int, int]) -> int:
    """Retrieves the length of an interval in seconds"""
    if interval[1] <= interval[0]:
        raise ValueError("Invalid interval: {:s}".format(str(interval)))
    return interval[1] - interval[0]


def filter_stream_video(stream: VideoBackend, kind: str, interval: Tuple[int, int], answer_text: str, reverse: bool,
                        box_height: int = 100, fade_amount_s: int = 3) -> VideoBackend:
    """Adds ffmpeg filters to the stream, processing a single video stream"""
    stream.trim(start_s=interval[0], end_s=interval[1])
    if reverse:
        stream.reverse()
    stream.fade_in_and_out(fade_amount_s, get_interval_length(interval))
    stream.scale_video()
    if kind == "answer":
        stream.draw_text_in_box(answer_text, get_interval_length(interval), box_height, move=False, top=True)
    return stream


def filter_stream_videos(stream: VideoBackend, kind: str, round_id: int, question_id: int,
                         repetitions: int, total_duration: int, box_height: int = 100,
                         spacer_txt: str = "", is_example: bool = False) -> VideoBackend:
    """Adds ffmpeg filters to the stream, processing the combined video stream"""
    if is_example:
        question_text = "Example {:s} for round {:d}".format(kind, round_id)
    else:
        question_text = "Question {:d}.{:d}".format(round_id, question_id)
    if repetitions > 1:
        question_text += " ({:d}x)".format(repetitions)

    stream.draw_text_in_box(question_text, total_duration, box_height, move=True, top=False)
    repeat_stream(stream, repetitions)
    if spacer_txt != "" and kind == "question":
        stream.add_spacer(spacer_txt, duration_s=2)
    return stream


def filter_stream_audio(stream: VideoBackend, interval: Tuple[int, int], reverse: bool,
                        fade_amount_s: int = 3) -> VideoBackend:
    """Adds ffmpeg filters to the stream, producing a single audio stream"""
    stream.trim(start_s=interval[0], end_s=interval[1])
    if reverse:
        stream.reverse()
    stream.fade_in_and_out(fade_amount_s, get_interval_length(interval))
    return stream


def filter_stream_audios(stream: VideoBackend, kind: str, repetitions: int, spacer_txt: str = "") -> VideoBackend:
    """Adds ffmpeg filters to the stream, producing the combined audio stream"""
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


def create_video(kind: str, round_id: int, question: Dict, question_id: int, output_dir: Path, answer_texts: List[str],
                 width: int = 1280, height: int = 720, backend: str = 'ffmpeg', spacer_txt: str = "",
                 use_cached_video_files: bool = False, is_example: bool = False) -> Path:
    """Creates a video for one question, either a question or an answer video"""
    # pylint: disable=too-many-locals
    assert kind in ["question", "answer"]

    repetitions = question.get("repetitions", 1) if kind == "question" else 1  # don't repeat the answer multiple times

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

    backend_cls = get_backend(backend)

    # Process the video(s)
    stream_videos = None
    total_duration = 0
    for video_id, video_info in enumerate(question[kind+"_video"]):
        ppq.io.log("Processing video input {:d}/{:d}".format(video_id + 1, len(question[kind+"_video"])))
        interval = ppq.io.get_interval_in_s(video_info["interval"])
        total_duration += get_interval_length(interval)
        reverse = video_info.get("reverse", False)
        stream_video = backend_cls(video_files[video_id], has_video=True, has_audio=False, width=width, height=height)
        stream_video = filter_stream_video(stream_video, kind, interval, answer_texts[video_id], reverse)
        if stream_videos is None:
            stream_videos = stream_video
        else:
            stream_videos.combine(stream_video)
    ppq.io.log("Processing final video")
    assert stream_videos is not None
    stream_videos = filter_stream_videos(stream_videos, kind, round_id, question_id, repetitions,
                                         total_duration, spacer_txt=spacer_txt, is_example=is_example)

    # Process the audio(s)
    stream_audios = None
    for audio_id, audio_info in enumerate(question[kind+"_audio"]):
        ppq.io.log("Processing audio input {:d}/{:d}".format(audio_id + 1, len(question[kind+"_audio"])))
        interval = ppq.io.get_interval_in_s(audio_info["interval"])
        reverse = audio_info.get("reverse", False)
        stream_audio = backend_cls(audio_files[audio_id], has_video=False, has_audio=True, width=width, height=height)
        stream_audio = filter_stream_audio(stream_audio, interval, reverse)
        if stream_audios is None:
            stream_audios = stream_audio
        else:
            stream_audios.combine(stream_audio)
    ppq.io.log("Processing final audio")
    assert stream_audios is not None
    stream_audio = filter_stream_audios(stream_audios, kind, repetitions, spacer_txt=spacer_txt)

    # Combine the audio and video
    stream_videos.add_audio(stream_audio)
    file_name_out = stream_videos.run(file_name, dry_run=not generate_video)

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
