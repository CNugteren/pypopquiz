"""Module with all video related functions, using one of the video backends"""

from pathlib import Path
from typing import Dict, List, Tuple, Optional

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


def filter_stream_video(stream: VideoBackend, kind: str, interval: Tuple[int, int], answer_texts: List[str],
                        reverse: bool, fade_amount_s: int = 3, delay_answer_text_s: int = 3,
                        answer_label_events: Optional[List] = None) -> VideoBackend:

    """Adds ffmpeg filters to the stream, processing a single video stream"""

    stream.trim(start_s=interval[0], end_s=interval[1])
    if reverse:
        stream.reverse()
    stream.scale_video()
    if kind == "answer":
        # (up to the) first two answers are joined together with " - " and shown at the top
        answer_text = " - ".join(answer_texts[:2])
        stream.draw_text_in_box(answer_text, get_interval_length(interval), move=False, top=True,
                                delay_in_sec=delay_answer_text_s)
        # Remainder is shown in the center of the video
        text_id = 0
        for answer_text in answer_texts[2:]:
            stream.draw_text(answer_text, 0.5 - 0.1 * len(answer_texts[2:]) + 0.2 * text_id)
            text_id += 1

        if answer_label_events is not None:
            for event in answer_label_events:
                interval_sec = pypopquiz.io.get_interval_in_fractional_s(event["interval"])
                # Create interval relative to start of clip instead of source video
                offset_interval_sec = (interval_sec[0] - interval[0], interval_sec[1] - interval[0])
                ppq.io.log('overlay_fading_text: {}'.format(event["answer"]))
                stream.draw_text(event["answer"],
                                 0.5 - 0.1 * len(answer_label_events) + 0.2 * text_id,
                                 interval=offset_interval_sec)
                text_id += 1

    stream.fade_in_and_out(fade_amount_s, get_interval_length(interval))
    return stream


def filter_stream_videos(stream: VideoBackend, kind: str, round_id: int, question_id: int,
                         repetitions: int, total_duration: int,
                         spacer_txt: str = "", is_example: bool = False) -> VideoBackend:
    """Adds ffmpeg filters to the stream, processing the combined video stream"""
    if is_example:
        question_text = "Example {:s} for round {:d}".format(kind, round_id)
    else:
        question_text = "Question {:d}.{:d}".format(round_id, question_id)
    if repetitions > 1:
        question_text += " ({:d}x)".format(repetitions)

    stream.draw_text_in_box(question_text, total_duration, move=True, top=False)
    repeat_stream(stream, repetitions)
    if spacer_txt != "" and (kind == "question" or is_example):
        stream.add_spacer(spacer_txt, duration_s=4)
    return stream


def filter_stream_audio(stream: VideoBackend, interval: Tuple[int, int], reverse: bool,
                        fade_amount_s: int = 3, beep_events: Optional[List] = None) -> VideoBackend:
    """Adds ffmpeg filters to the stream, producing a single audio stream"""
    if beep_events is not None:
        for event in beep_events:
            beep = event["interval"]
            beep_sec = pypopquiz.io.get_interval_in_fractional_s(beep)
            stream.replace_audio_by_beep(interval=beep_sec)
    stream.trim(start_s=interval[0], end_s=interval[1])
    if reverse:
        stream.reverse()
    stream.fade_in_and_out(fade_amount_s, get_interval_length(interval))
    return stream


def filter_stream_audios(stream: VideoBackend, kind: str, repetitions: int,
                         spacer_txt: str = "", is_example: bool = False) -> VideoBackend:
    """Adds ffmpeg filters to the stream, producing the combined audio stream"""
    repeat_stream(stream, repetitions)
    if spacer_txt != "" and (kind == "question" or is_example):
        stream.add_silence(duration_s=4)  # for the spacer
    stream.normalize_audio()
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


def unlink_if_exists_and_not_using_as_cached(file_name: Path, use_cached_video_files: bool) -> bool:
    """Conditionally unlink video file, unless we want to use cached videos."""
    generate_video = True
    if file_name.exists():
        if use_cached_video_files:
            generate_video = False
        else:
            file_name.unlink()  # deletes a previous version
    return generate_video


def create_video(kind: str, round_id: int, question: Dict, question_id: int, output_dir: Path, round_dir: Path,
                 answer_texts: List[List[str]], width: int, height: int,
                 backend: str = 'ffmpeg', spacer_txt: str = "",
                 use_cached_video_files: bool = False, is_example: bool = False) -> Path:
    """Creates a video for one question, either a question or an answer video"""
    # pylint: disable=too-many-locals,too-many-statements
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
    file_name = round_dir / ("{:02d}_{:02d}_{:s}.{:s}".format(round_id, question_id, kind, target_format))
    generate_video = unlink_if_exists_and_not_using_as_cached(file_name, use_cached_video_files)

    backend_cls = get_backend(backend)

    # Process the video(s)
    stream_videos = None
    total_duration = 0
    for video_id, video_info in enumerate(question[kind + "_video"]):
        ppq.io.log("Processing video input {:d}/{:d}".format(video_id + 1, len(question[kind + "_video"])))

        interval = ppq.io.get_interval_in_s(video_info["interval"])
        total_duration += get_interval_length(interval)
        reverse = video_info.get("reverse", False)
        answer_label_events = video_info.get("answer_label_events", [])
        crossfade_duration = video_info.get("crossfade_duration", 0)

        stream_video = backend_cls(video_files[video_id], has_video=True, has_audio=False, width=width, height=height)

        # Use modulo-answer texts here, to catch the cases where there is 1 answer, while the
        # answer video is built from 2 (concatenated) clips
        stream_video = filter_stream_video(stream_video, kind, interval, answer_texts[video_id % len(answer_texts)],
                                           reverse, answer_label_events=answer_label_events)

        if stream_videos is None:
            stream_videos = stream_video
        else:
            stream_videos.combine(stream_video, crossfade_duration=crossfade_duration)

    ppq.io.log("Processing final video")
    assert stream_videos is not None
    stream_videos = filter_stream_videos(stream_videos, kind, round_id, question_id, repetitions,
                                         total_duration, spacer_txt=spacer_txt, is_example=is_example)

    # Process the audio(s)
    stream_audios = None
    for audio_id, audio_info in enumerate(question[kind + "_audio"]):
        ppq.io.log("Processing audio input {:d}/{:d}".format(audio_id + 1, len(question[kind + "_audio"])))

        interval = ppq.io.get_interval_in_s(audio_info["interval"])
        reverse = audio_info.get("reverse", False)
        beep_events = audio_info.get("beeps_events", [])
        crossfade_duration = audio_info.get("crossfade_duration", 0)

        stream_audio = backend_cls(audio_files[audio_id], has_video=False, has_audio=True, width=width, height=height)
        stream_audio = filter_stream_audio(stream_audio, interval, reverse, beep_events=beep_events)

        if stream_audios is None:
            stream_audios = stream_audio
        else:
            stream_audios.combine(stream_audio, crossfade_duration=crossfade_duration)

    ppq.io.log("Processing final audio")
    assert stream_audios is not None
    stream_audio = filter_stream_audios(stream_audios, kind, repetitions, spacer_txt=spacer_txt, is_example=is_example)

    # Combine the audio and video
    stream_videos.add_audio(stream_audio)
    file_name_out = stream_videos.run(file_name, dry_run=not generate_video)

    return file_name_out


def combine_videos(video_files: List[Path], kind: str, round_id: int, output_dir: Path, width: int, height: int,
                   backend: str = 'ffmpeg') -> None:
    """Combines a list of video files together into a single video"""
    backend_cls = get_backend(backend)

    assert video_files  # assumes at least one item
    stream = backend_cls(video_files[0], has_video=True, has_audio=True, width=width, height=height)
    for video_file in video_files[1:]:
        new_stream = backend_cls(video_file, has_video=True, has_audio=True, width=width, height=height)
        stream.combine(new_stream)

    file_name = output_dir / ("{:02d}_{:s}{:s}".format(round_id, kind, video_files[0].suffix))
    stream.run(file_name)


def create_text_video(file_name: Path, source_texts: List[str], duration: int,
                      width: int, height: int, use_cached_video_files: bool = False,
                      backend: str = 'ffmpeg') -> Path:
    """Generates a video with text on a black background"""
    backend_cls = get_backend(backend)
    stream = backend_cls.create_empty_stream(duration, width=width, height=height)
    num_texts = len(source_texts)
    for text_id, source_text in enumerate(source_texts):
        stream.draw_text(source_text, 0.5 - 0.1 * num_texts + 0.2 * text_id)

    stream.fade_in_and_out(1, duration)

    audio = backend_cls.create_silent_stream(duration, width=width, height=height)
    stream.add_audio(audio)

    generate_video = unlink_if_exists_and_not_using_as_cached(file_name, use_cached_video_files)

    file_name_out = stream.run(file_name, dry_run=not generate_video)
    return file_name_out


def create_video_from_single_image(file_name: Path, input_image: Path, duration: int,
                                   width: int, height: int, backend: str = 'ffmpeg') -> None:
    """Generates a video with a specific background"""
    backend_cls = get_backend(backend)
    stream = backend_cls.create_single_image_stream(input_image, duration, width=width, height=height)
    stream.run(file_name)
