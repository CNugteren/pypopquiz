"""Moviepy backend for video editing"""

from pathlib import Path

import moviepy.editor
from moviepy.editor import vfx

import pypopquiz as ppq


class Moviepy(ppq.backends.backend.Backend):
    """Moviepy backend."""

    def __init__(self, source_file: Path, width: int = 1280, height: int = 720) -> None:
        super().__init__()
        if source_file.suffix in ('.mp3', '.wav', ):
            # Create a black clip with the audio file pasted on top
            audio = moviepy.editor.AudioFileClip(str(source_file))
            color = moviepy.editor.ColorClip(size=(width, height), color=(0, 0, 0), duration=audio.duration)
            self.video = color.set_audio(audio)
            # Need to select something as the fps (colorclip has no inherent framerate)
            self.video = self.video.set_fps(24)
        else:
            # Assume video otherwise
            self.video = moviepy.editor.VideoFileClip(str(source_file))

    def trim(self, start_s: int, end_s: int) -> None:
        """Trims a video to a given start and end time measured in seconds"""
        self.video = self.video.subclip(start_s, end_s)

    def repeat(self) -> None:
        """Concatenates a video and audio stream with itself to make a twice as long video"""
        self.video = moviepy.editor.concatenate_videoclips([self.video, self.video])

    def fade_in_and_out(self, duration_s: int, video_length_s: int) -> None:
        """Adds a fade-in and fade-out to/from black for the audio and video stream"""
        self.video = self.video.fx(vfx.fadein, duration_s).fx(vfx.fadeout, duration_s)

    def scale_video(self, width: int, height: int) -> None:
        """Scales the video and pads if necessary to the requested dimensions"""
        self.video = self.video.fx(vfx.resize, (width, height))  # TODO: padding with black

    def draw_text_in_box(self, video_text: str, length: int, width: int, height: int,
                         box_height: int, move: bool, top: bool) -> None:
        """Draws a semi-transparent box either at the top or bottom and writes text in it, optionally scrolling by"""
        y_location = 0 if top else height - box_height
        txt = moviepy.editor.TextClip(video_text, font='Amiri-regular', color='white', fontsize=30)

        video_w, _ = self.video.size

        # Paste the text on top of a colored bar
        txt_col = txt.on_color(
            size=(video_w + txt.w, box_height),  # automatic height: txt.h + 10
            color=(0, 0, 0), pos=(video_w / 20, 'center'), col_opacity=0.6
        )

        if move:
            txt_mov = txt_col.set_pos(lambda t: (max(0, int(video_w - 0.5 * video_w * t)), y_location))
        else:
            txt_mov = txt_col

        duration = self.video.duration
        self.video = moviepy.editor.CompositeVideoClip([self.video, txt_mov])
        self.video.duration = duration


    def run(self, file_name: Path) -> None:
        """Runs the backend to create the video, applying all the filters"""
        self.video.write_videofile(str(file_name.with_suffix('.mp4')))
