"""Moviepy backend for video editing"""

import math
from pathlib import Path
import typing
from typing import Callable, List, Optional, Tuple, Union

import numpy as np

import moviepy
import moviepy.editor as med  # pylint: disable=no-name-in-module,import-error
from moviepy.decorators import audio_video_fx  # pylint: disable=import-error,no-name-in-module
from moviepy.editor import afx  # pylint: disable=import-error
from moviepy.editor import vfx  # pylint: disable=import-error
from moviepy.editor import transfx  # pylint: disable=import-error

import pypopquiz as ppq
import pypopquiz.backends.backend


def silence(_) -> float:
    """Callback function for make_frame() on AudioClip to generate silence."""
    return 0


def make_sin(time_seconds: np.array) -> List[float]:
    """Create a single tone."""
    out = [np.sin(1500 * np.pi * time_seconds)]
    return out


@audio_video_fx
def tone_in_interval(clip: med.AudioClip, interval: Tuple[float, float], freq_hz: int):
    """Fx that replaces interval by a beep."""

    def beeped(get_frame: Callable, time_seconds: Union[float, np.array]):
        """Fx callback that replaces the original sounds with a tone in an interval."""
        t = time_seconds  # pylint: disable=invalid-name
        original = get_frame(t)

        if np.isscalar(t):
            t = typing.cast(float, t)  # pylint: disable=invalid-name
            if interval[0] < t < interval[1]:
                t_offset = t - interval[0]
                return [np.sin(freq_hz * np.pi * t_offset)]

            # Tone is not active:
            return original

        # t is an array of timestamps:
        selector = np.logical_and(interval[0] < t, interval[1] > t)  # pylint: disable=assignment-from-no-return
        t_offset = t - interval[0]
        tone = np.array(np.sin(freq_hz * np.pi * t_offset))

        channels_out = [np.where(selector, tone, channel) for channel in original.T]
        return np.vstack(channels_out).T

    return clip.fl(beeped, keep_duration=True)


class Moviepy(pypopquiz.backends.backend.Backend):
    """Moviepy backend."""
    DEFAULT_FPS = 25

    def __init__(self, source_file: Path, has_video: bool, has_audio: bool,
                 width: int, height: int, duration: Optional[float] = None) -> None:
        super().__init__(has_video, has_audio, width, height)
        # Keep a reference to the original object that read input files.
        # moviepy leaks process references even if these objects go out of scope,
        # and hence we need to close them explicitly at the end of the run() method.
        self.reader_refs = []  # type: List[moviepy.clip.Clip]

        audio_input_file = source_file.suffix in ('.mp3', '.wav',)
        image_input_file = source_file.suffix in ('.png', '.jpg')
        if has_video:
            if audio_input_file:
                # Create a black clip with the audio file pasted on top
                audio = med.AudioFileClip(str(source_file))
                self.reader_refs.append(audio)

                self.clip = self.create_color_clip((width, height), (0, 0, 0), audio.duration)
                self.clip = self.clip.set_audio(audio)
            elif image_input_file:
                duration = typing.cast(float, duration)
                self.clip = med.ImageClip(str(source_file), duration=duration)
            else:
                # Assume video otherwise
                self.clip = med.VideoFileClip(str(source_file), audio=has_audio)
                self.clip.set_fps(Moviepy.DEFAULT_FPS)

                self.reader_refs.append(self.clip)

        elif has_audio:
            # Work only on audio from here on out
            if source_file.is_file():
                # Extract audio stream from file (even if it is a video file)
                self.clip = med.AudioFileClip(str(source_file))
                self.reader_refs.append(self.clip)
            else:
                # A black clip w/o audio
                duration = typing.cast(float, duration)
                self.clip = self.create_color_clip((width, height), (0, 0, 0), duration)
        else:
            # Blank video
            assert duration is not None
            duration = typing.cast(float, duration)
            self.clip = self.create_color_clip((width, height), (0, 0, 0), duration)
            self.has_video = True

        # Workaround moviepy issues: Occasionally, clips gain fractional seconds of duration
        # due to rounding errors. Flooring them back keeps things reasonably sane most of the time.
        self.clip = self.clip.set_duration(math.floor(self.clip.duration))

    @classmethod
    def create_empty_stream(cls, duration: int, width: int, height: int) -> 'Moviepy':
        """Creates a video of a certain duration with a black still image"""
        return cls(source_file=Path(''), has_video=False, has_audio=False, width=width, height=height,
                   duration=duration)

    @classmethod
    def create_silent_stream(cls, duration: float, width: int, height: int) -> 'Moviepy':
        """Creates audio of a certain duration with no sound"""
        return cls(source_file=Path(''), has_video=False, has_audio=True, width=width, height=height,
                   duration=duration)

    @classmethod
    def create_single_image_stream(cls, input_image: Path, duration: int,
                                   width: int, height: int) -> 'Moviepy':
        """Creates a video of a certain duration with a single still image"""
        stream = cls(Path(input_image), has_video=True, has_audio=False, width=width, height=height,
                     duration=duration)
        stream.scale_video()
        return stream

    @staticmethod
    def create_color_clip(size: Tuple[int, int], color: Tuple[int, int, int], duration: float) -> med.ColorClip:
        """Create a new color clip with a valid FPS."""
        clip = med.ColorClip(size=size, color=color, duration=duration)
        # Need to select something as the fps (colorclip has no inherent framerate)
        clip = clip.set_fps(Moviepy.DEFAULT_FPS)  # pylint: disable=assignment-from-no-return
        return clip

    def trim(self, start_s: int, end_s: int) -> None:
        """Trims a video to a given start and end time measured in seconds"""
        self.clip = self.clip.subclip(start_s, end_s)

    def repeat(self) -> None:
        """Concatenates a video and audio stream with itself to make a twice as long video"""
        if self.has_video:
            self.clip = med.concatenate_videoclips([self.clip, self.clip])
        else:
            self.clip = med.concatenate_audioclips([self.clip, self.clip])

    def combine(self, other: 'Moviepy', other_first: bool = False,  # type: ignore
                crossfade_duration: float = 0) -> None:
        """Combines this video stream with another stream"""
        self.reader_refs += other.reader_refs
        clips = [other.clip, self.clip] if other_first else [self.clip, other.clip]

        if self.has_video and other.has_video:
            if crossfade_duration == 0:
                self.clip = med.concatenate_videoclips(clips)
            else:
                # Have clips[1] start while clips[0] is not finished yet
                clips[1] = clips[1].set_start(max(0, clips[0].duration - crossfade_duration))
                clips[1] = clips[1].fx(transfx.crossfadein, crossfade_duration)
                self.clip = med.CompositeVideoClip([clips[0], clips[1]])
                # TODO: consider calling set_duration?
                self.clip.duration = clips[0].duration + clips[1].duration - crossfade_duration
        else:
            if crossfade_duration == 0:
                assert self.has_video is False and other.has_video is False
                self.clip = med.concatenate_audioclips(clips)
            else:
                # Audio crossfade in: start earlier, fade in with normal audio_fadein effect.
                clips[1] = clips[1].set_start(max(0, clips[0].duration - crossfade_duration))
                clips[1] = clips[1].fx(afx.audio_fadein, crossfade_duration)
                self.clip = med.CompositeAudioClip([clips[0], clips[1]])
                self.clip.duration = clips[0].duration + clips[1].duration - crossfade_duration

    def fade_in_and_out(self, duration_s: int, video_length_s: int, fade_in: bool = True,
                        fade_out: bool = True) -> None:
        """Adds a fade-in and fade-out to/from black for the audio and video stream"""
        if self.has_video:
            if fade_in:
                self.clip = self.clip.fx(vfx.fadein, duration_s).\
                    fx(afx.audio_fadein, duration_s)

            if fade_out:
                self.clip = self.clip.fx(vfx.fadeout, duration_s).\
                    fx(afx.audio_fadeout, duration_s)
        else:
            if fade_in:
                self.clip = self.clip.fx(afx.audio_fadein, duration_s)

            if fade_out:
                self.clip = self.clip.fx(afx.audio_fadeout, duration_s)

    @staticmethod
    def get_scaled_size(w_in: int, h_in: int, max_w_out: int, max_h_out: int) -> Tuple[int, int]:
        """Return new dimensions using aspect-ratio preserving scaling to fit a certain bounding box."""
        if w_in == max_w_out and h_in == max_h_out:
            return w_in, h_in

        target_w_factor = max_w_out / w_in
        target_h_factor = max_h_out / h_in

        scale_factor = min(target_w_factor, target_h_factor)
        scale_w_to = int(w_in * scale_factor)
        scale_h_to = int(h_in * scale_factor)

        return scale_w_to, scale_h_to

    def scale_video(self) -> None:
        """Scales the video and pads if necessary to the requested dimensions"""
        assert self.has_video
        video_w, video_h = self.clip.size

        if video_w == self.width and video_h == self.height:
            return

        scale_w_to, scale_h_to = self.get_scaled_size(video_w, video_h, self.width, self.height)

        # Scale clip
        scaled_clip = self.clip.fx(vfx.resize, (scale_w_to, scale_h_to))  # TODO: padding with black
        scaled_clip = scaled_clip.set_position(pos=((self.width - scale_w_to) // 2, (self.height - scale_h_to) // 2))

        # Paste on black background
        duration = self.clip.duration
        clips = [self.create_color_clip((self.width, self.height), (0, 0, 0), duration), scaled_clip]
        self.clip = med.CompositeVideoClip(clips)
        self.clip = self.clip.set_duration(duration)

    def draw_text(self, video_text: str, height_fraction: float,
                  interval: Optional[Tuple[float, float]] = None) -> None:
        """Draws text in the center of the video at a certain height fraction"""
        assert self.has_video
        duration_s = 0  # Don't care, uses interval
        if interval is None:
            interval = (0, self.clip.duration)
        self.clip = Moviepy.draw_text_in_box_on_video(
            self.clip, video_text, duration_s, self.width, self.height, box_height=self.get_box_height(),
            move=False, top=False, on_box=False, center=True, vpos=height_fraction,
            interval=interval, fontsize=self.get_font_size()
        )

    def draw_text_in_box(self, video_text: str, length: int, move: bool, top: bool,
                         delay_in_sec: Optional[int] = None) -> None:
        """Draws a semi-transparent box either at the top or bottom and writes text in it, optionally scrolling by"""
        assert self.has_video
        self.clip = Moviepy.draw_text_in_box_on_video(
            self.clip, video_text, length, self.width, self.height, self.get_box_height(),
            move, top, fontsize=self.get_font_size()
        )

    @staticmethod
    def draw_text_in_box_on_video(video: med.VideoFileClip, video_text: str,
                                  length: float, width: int, height: int, box_height: int, move: bool,
                                  top: bool, on_box: bool = True, center: bool = False,
                                  vpos: Optional[float] = None,
                                  interval: Optional[Tuple[float, float]] = None,
                                  fontsize=30) -> med.CompositeVideoClip:
        """Draws a semi-transparent box either at the top or bottom and writes text in it, optionally scrolling by"""
        clips = []

        y_location = 0 if top else height - box_height
        y_location = height // 2 if center else y_location

        if vpos is not None:
            y_location = int(height * vpos)

        video_w, _ = video.size

        if on_box:
            color_clip = med.ColorClip(size=(video_w, box_height), color=(0, 0, 0))
            color_clip = color_clip.set_fps(Moviepy.DEFAULT_FPS)  # pylint: disable=assignment-from-no-return

            color_clip = color_clip.set_opacity(0.5)  # pylint: disable=assignment-from-no-return
            color_clip = color_clip.set_position(pos=(0, y_location))
            clips.append(color_clip)

        stroke_color = 'black' if not on_box else None
        txt = med.TextClip(video_text, font='Bauhaus-93', color='white', stroke_color=stroke_color, fontsize=fontsize)

        txt_y_location = (box_height - txt.h) // 2 + y_location

        if center:
            txt_left_margin = (width - txt.w) // 2
        else:
            txt_left_margin = 20

        # pylint: disable=assignment-from-no-return
        if move:
            txt_mov = txt.set_position(lambda t: (max(txt_left_margin,
                                                      round(video_w - video_w * t / float(length))), txt_y_location))
        else:
            txt_mov = txt.set_position((txt_left_margin, txt_y_location))
        # pylint: enable=assignment-from-no-return
        txt_mov = txt_mov.set_fps(Moviepy.DEFAULT_FPS)  # pylint: disable=assignment-from-no-return

        if interval:
            # Fade text in and out
            fade_duration = 1  # second
            txt_mov = txt_mov.set_duration(interval[1] - interval[0] + fade_duration * 2)
            txt_mov = txt_mov.set_start(max(0, interval[0] - fade_duration))

            txt_mov = txt_mov.fx(vfx.fadein, fade_duration).\
                fx(vfx.fadeout, fade_duration)

        clips.append(txt_mov)

        duration = video.duration
        # Add the input video as the first in the list
        clips = [video] + clips

        # Build a new composition out of the original clip and the text overlay.
        # video = med.CompositeVideoClip(clips, use_bgclip=interval is not None)
        video = med.CompositeVideoClip(clips)
        video.duration = duration
        return video

    def add_spacer(self, text: str, duration_s: float) -> None:
        """Add a text spacer to the start of the clip."""
        assert self.has_video
        # create a black screen, of duration_s seconds.
        color = med.ColorClip(size=(self.width, self.height), color=(0, 0, 0), duration=duration_s)
        color = color.set_fps(Moviepy.DEFAULT_FPS)  # pylint: disable=assignment-from-no-return
        spacer = Moviepy.draw_text_in_box_on_video(
            color, text, duration_s, self.width, self.height, box_height=self.get_box_height(),
            move=True, top=False, on_box=False
        )
        self.clip = med.concatenate_videoclips([spacer, self.clip])

    def add_silence(self, duration_s: float) -> None:
        """Add a silence of a certain duration the an audio clip."""
        silence_clip = med.AudioClip(silence, duration=duration_s)
        self.clip = med.concatenate_audioclips([silence_clip, self.clip])

    def normalize_audio(self) -> None:
        """Normalizes audio volume"""
        assert self.has_audio
        # TODO: Implement

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

        if isinstance(other.clip, med.AudioClip):
            audio = other.clip
        else:
            audio = other.clip.audio

        self.clip = self.clip.set_audio(audio)

    def audio_normalize(self) -> None:
        """Normalize the audio volume."""
        if self.has_audio:
            self.clip = self.clip.fx(afx.audio_normalize)

    def add_beep_audio(self) -> None:
        """Add a single tone as audio track."""
        tone = med.AudioClip(make_sin, duration=self.clip.duration)
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
                self.clip.write_videofile(str(tmp_out), threads=2)  # write_logfile=True

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
