"""Moviepy backend for video editing"""

from pathlib import Path

import moviepy.editor
from moviepy.editor import afx
from moviepy.editor import vfx

import pypopquiz as ppq
import pypopquiz.backends.backend


class Moviepy(pypopquiz.backends.backend.Backend):
    """Moviepy backend."""

    def __init__(self, source_file: Path, width: int = 1280, height: int = 720) -> None:
        super().__init__(width, height)
        if source_file.suffix in ('.mp3', '.wav', ):
            # Create a black clip with the audio file pasted on top
            audio = moviepy.editor.AudioFileClip(str(source_file))

            # Keep a reference to the original object that read the file.
            # moviepy leaks process references, and hence we need to close them
            # explicitly at the end of the run() method.
            self.reader_ref = audio

            self.video = moviepy.editor.ColorClip(size=(width, height), color=(0, 0, 0), duration=audio.duration)
            self.video = self.video.set_audio(audio)
            # Need to select something as the fps (colorclip has no inherent framerate)
            self.video = self.video.set_fps(24)
        else:
            # Assume video otherwise
            self.video = moviepy.editor.VideoFileClip(str(source_file))

            # Keep a reference to the original object that read the file.
            # moviepy leaks process references, and hence we need to close them
            # explicitly at the end of the run() method.
            self.reader_ref = self.video

    def trim(self, start_s: int, end_s: int) -> None:
        """Trims a video to a given start and end time measured in seconds"""
        self.video = self.video.subclip(start_s, end_s)

    def repeat(self) -> None:
        """Concatenates a video and audio stream with itself to make a twice as long video"""
        self.video = moviepy.editor.concatenate_videoclips([self.video, self.video])

    def combine(self, other: 'Moviepy') -> None:  # type: ignore
        """Combines this video stream with another stream"""
        self.video = moviepy.editor.concatenate_videoclips([self.video, other.video])

    def fade_in_and_out(self, duration_s: int, video_length_s: int) -> None:
        """Adds a fade-in and fade-out to/from black for the audio and video stream"""
        self.video = self.video.fx(vfx.fadein, duration_s).\
            fx(vfx.fadeout, duration_s).\
            fx(afx.audio_fadein, duration_s).\
            fx(afx.audio_fadeout, duration_s)

    def scale_video(self) -> None:
        """Scales the video and pads if necessary to the requested dimensions"""
        self.video = self.video.fx(vfx.resize, (self.width, self.height))  # TODO: padding with black

    def draw_text_in_box(self, video_text: str, length: int, box_height: int, move: bool, top: bool) -> None:
        """Draws a semi-transparent box either at the top or bottom and writes text in it, optionally scrolling by"""
        self.video = Moviepy.draw_text_in_box_on_video(
            self.video, video_text, length, self.height, box_height, move, top
        )

    @staticmethod
    def draw_text_in_box_on_video(video: moviepy.editor.VideoFileClip, video_text: str,
                                  length: float, height: int, box_height: int, move: bool,
                                  top: bool) -> moviepy.editor.CompositeVideoClip:
        """Draws a semi-transparent box either at the top or bottom and writes text in it, optionally scrolling by"""
        y_location = 0 if top else height - box_height
        txt = moviepy.editor.TextClip(video_text, font='Arial', color='white', fontsize=30)

        video_w, _ = video.size

        # Paste the text on top of a colored bar
        txt_col = txt.on_color(size=(video_w + txt.w, box_height),  # automatic height: txt.h + 10
                               color=(0, 0, 0), pos=(video_w / 20, 'center'), col_opacity=0.6)

        if move:
            txt_mov = txt_col.set_position(lambda t: (max(0, int(video_w - video_w * t / float(length))), y_location))
        else:
            txt_mov = txt_col

        duration = video.duration
        video = moviepy.editor.CompositeVideoClip([video, txt_mov])
        video.duration = duration
        return video

    def add_spacer(self, text: str, duration_s: float) -> None:
        """Add a text spacer to the start of the clip."""
        # create a black screen, of duration_s seconds.
        color = moviepy.editor.ColorClip(size=(self.width, self.height), color=(0, 0, 0), duration=duration_s)
        spacer = Moviepy.draw_text_in_box_on_video(
            color, text, duration_s, self.height, box_height=100, move=True, top=False
        )
        self.video = moviepy.editor.concatenate_videoclips([spacer, self.video])

    def run(self, file_name: Path, dry_run: bool = False) -> Path:
        """Runs the backend to create the video, applying all the filters"""
        # Force mp4 extension, even if the original file was audio-only.
        file_name_out = file_name.with_suffix('.mp4')
        if not dry_run:
            self.video.write_videofile(str(file_name_out))

        # Close the file reader (typically terminates an ffmpeg process)
        self.reader_ref.close()

        return file_name_out
