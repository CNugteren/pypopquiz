"""Moviepy backend for video editing"""

from pathlib import Path
from typing import Callable, List, Tuple, Union

import numpy as np


import moviepy.editor
from moviepy.editor import afx
from moviepy.editor import vfx
from moviepy.decorators import audio_video_fx

import pypopquiz as ppq
import pypopquiz.backends.backend


def silence(_) -> float:
    """Callback function for make_frame() on AudioClip to generate silence."""
    return 0


def make_sin(t) -> float:
    out = [np.sin(1500 * np.pi * t)]
    # print(t)
    return out


@audio_video_fx
def tone_in_interval(clip: moviepy.editor.AudioClip, interval: Tuple[float, float], freq_hz: int):
    """Fx that replaces interval by a beep."""

    def beeped(get_frame: Callable, t: Union[float, List]):
        """Fx callback that replaces the original sounds with a tone in an interval."""
        original = get_frame(t)

        if np.isscalar(t):
            if interval[0] < t < interval[1]:
                t_offset = t - interval[0]
                out = [np.sin(1500 * np.pi * t_offset)]
            else:
                out = original
        else:
            selector0 = interval[0] < t
            selector1 = interval[1] > t
            selector = np.logical_and(selector0, selector1)

            t_offset = t - interval[0]
            tone = np.array(np.sin(freq_hz * np.pi * t_offset))

            channels_out = []
            channels = original.T
            for channel in channels:
                channels_out.append(np.where(selector, tone, channel))

            out = np.vstack(channels_out).T
        return out
    return clip.fl(beeped, keep_duration=True)


class Moviepy(pypopquiz.backends.backend.Backend):
    """Moviepy backend."""

    def __init__(self, source_file: Path, has_video: bool, has_audio: bool,
                 width: int = 1280, height: int = 720) -> None:
        super().__init__(has_video, has_audio, width, height)
        # Keep a reference to the original object that read input files.
        # moviepy leaks process references even if these objects go out of scope,
        # and hence we need to close them explicitly at the end of the run() method.
        self.reader_refs = []  # type: List[moviepy.clip.Clip]

        if has_video:
            audio_input_file = source_file.suffix in ('.mp3', '.wav', )
            if audio_input_file:
                # Create a black clip with the audio file pasted on top
                audio = moviepy.editor.AudioFileClip(str(source_file))
                self.reader_refs.append(audio)

                self.clip = moviepy.editor.ColorClip(size=(width, height), color=(0, 0, 0), duration=audio.duration)
                self.clip = self.clip.set_audio(audio)
                # Need to select something as the fps (colorclip has no inherent framerate)
                self.clip = self.clip.set_fps(24)
            else:
                # Assume video otherwise
                self.clip = moviepy.editor.VideoFileClip(str(source_file), audio=has_audio)
                self.reader_refs.append(self.clip)

        else:
            assert has_audio
            # Work only on audio from here on out
            self.clip = moviepy.editor.AudioFileClip(str(source_file))
            self.reader_refs.append(self.clip)

    def trim(self, start_s: int, end_s: int) -> None:
        """Trims a video to a given start and end time measured in seconds"""
        self.clip = self.clip.subclip(start_s, end_s)

    def repeat(self) -> None:
        """Concatenates a video and audio stream with itself to make a twice as long video"""
        if self.has_video:
            self.clip = moviepy.editor.concatenate_videoclips([self.clip, self.clip])
        else:
            self.clip = moviepy.editor.concatenate_audioclips([self.clip, self.clip])

    def combine(self, other: 'Moviepy') -> None:  # type: ignore
        """Combines this video stream with another stream"""
        self.reader_refs += other.reader_refs

        if self.has_video and other.has_video:
            self.clip = moviepy.editor.concatenate_videoclips([self.clip, other.clip])
        else:
            assert self.has_video is False and other.has_video is False
            self.clip = moviepy.editor.concatenate_audioclips([self.clip, other.clip])

    def fade_in_and_out(self, duration_s: int, video_length_s: int) -> None:
        """Adds a fade-in and fade-out to/from black for the audio and video stream"""
        if self.has_video:

            self.clip = self.clip.fx(vfx.fadein, duration_s).\
                fx(vfx.fadeout, duration_s).\
                fx(afx.audio_fadein, duration_s).\
                fx(afx.audio_fadeout, duration_s)
        else:
            self.clip = self.clip.fx(afx.audio_fadein, duration_s).\
                fx(afx.audio_fadeout, duration_s)

    def scale_video(self) -> None:
        """Scales the video and pads if necessary to the requested dimensions"""
        assert self.has_video
        self.clip = self.clip.fx(vfx.resize, (self.width, self.height))  # TODO: padding with black

    def draw_text_in_box(self, video_text: str, length: int, box_height: int, move: bool, top: bool) -> None:
        """Draws a semi-transparent box either at the top or bottom and writes text in it, optionally scrolling by"""
        assert self.has_video
        self.clip = Moviepy.draw_text_in_box_on_video(
            self.clip, video_text, length, self.height, box_height, move, top
        )

    @staticmethod
    def draw_text_in_box_on_video(video: moviepy.editor.VideoFileClip, video_text: str,
                                  length: float, height: int, box_height: int, move: bool,
                                  top: bool, on_box: bool = True) -> moviepy.editor.CompositeVideoClip:
        """Draws a semi-transparent box either at the top or bottom and writes text in it, optionally scrolling by"""
        clips = [video]

        y_location = 0 if top else height - box_height
        video_w, _ = video.size
        txt_left_margin = 50

        if on_box:
            color_clip = moviepy.editor.ColorClip(size=(video_w, box_height), color=(0, 0, 0))
            color_clip = color_clip.set_opacity(0.6)  # pylint: disable=assignment-from-no-return
            color_clip = color_clip.set_position(pos=(0, y_location))
            clips.append(color_clip)

        txt = moviepy.editor.TextClip(video_text, font='Arial', color='white', fontsize=30)
        txt_y_location = (box_height - txt.h) // 2 + y_location

        # pylint: disable=assignment-from-no-return
        if move:
            txt_mov = txt.set_position(lambda t: (max(txt_left_margin,
                                                      round(video_w - video_w * t / float(length))), txt_y_location))
        else:
            txt_mov = txt.set_position((txt_left_margin, txt_y_location))
        # pylint: enable=assignment-from-no-return

        clips.append(txt_mov)

        duration = video.duration
        video = moviepy.editor.CompositeVideoClip(clips)
        video.duration = duration
        return video

    def add_spacer(self, text: str, duration_s: float) -> None:
        """Add a text spacer to the start of the clip."""
        assert self.has_video
        # create a black screen, of duration_s seconds.
        color = moviepy.editor.ColorClip(size=(self.width, self.height), color=(0, 0, 0), duration=duration_s)
        color = color.set_fps(30)  # pylint: disable=assignment-from-no-return
        spacer = Moviepy.draw_text_in_box_on_video(
            color, text, duration_s, self.height, box_height=100, move=True, top=False, on_box=False
        )
        self.clip = moviepy.editor.concatenate_videoclips([spacer, self.clip])

    def add_silence(self, duration_s: float) -> None:
        """Add a silence of a certain duration the an audio clip."""
        silence_clip = moviepy.editor.AudioClip(silence, duration=duration_s)
        self.clip = moviepy.editor.concatenate_audioclips([silence_clip, self.clip])

    def reverse(self) -> None:
        """Reverses an entire audio or video clip."""
        duration = self.clip.duration
        self.clip = self.clip.fl_time(lambda t: self.clip.duration - t, keep_duration=True)
        if self.has_video and self.clip.audio is not None:
            # When reversing a video clip, moviepy forgets to set the audio duration,
            # and complaints later on.
            self.clip.audio.duration = duration

    def add_audio(self, other: 'Moviepy') -> None:  # type: ignore
        """Adds audio to this video clip from another source"""
        assert self.has_video and other.has_audio

        self.reader_refs += other.reader_refs

        self.has_audio = True

        if isinstance(other.clip, moviepy.editor.AudioClip):
            audio = other.clip
        else:
            audio = other.clip.audio

        self.clip = self.clip.set_audio(audio)

    def audio_normalize(self) -> None:
        if self.has_audio:
            self.clip = self.clip.fx(afx.audio_normalize)

    def add_beep_audio(self) -> None:
        """Add a single tone as audio track."""
        tone = moviepy.editor.AudioClip(make_sin, duration=self.clip.duration)
        self.clip = self.clip.set_audio(tone)

    def replace_audio_by_beep(self, interval: Tuple[float, float], freq_hz: int = 1500) -> None:
        """Replace the original audio by a beep in a particular interval."""
        self.clip = self.clip.fx(tone_in_interval, interval, freq_hz=freq_hz)

    def run(self, file_name: Path, dry_run: bool = False) -> Path:
        """Runs the backend to create the video, applying all the filters"""
        file_name_out = file_name
        if file_name.suffix in ('.mp3', '.wav', ):
            # Force mp4 extension, even if the original file was audio-only.
            file_name_out = file_name.with_suffix('.mp4')

        if not dry_run:
            with Moviepy.tmp_intermediate_file(file_name_out) as tmp_out:
                self.clip.write_videofile(str(tmp_out))
                # self.clip.write_videofile(str(tmp_out), threads=2)

        # Close the file reader (typically terminates an ffmpeg process)
        self.close_readers()

        return file_name_out

    def close_readers(self):
        """Close potentially open file references on clip objects."""
        # This is best-effort garbage collection: exceptions are silently passed.
        for ref in self.reader_refs:
            try:
                ref.close()
            except Exception:  # pylint: disable=broad-except
                pass

        self.reader_refs = []
