"""FFMPEG backend for video editing"""

import subprocess
from pathlib import Path
from typing import Any

import pkg_resources
import ffmpeg

import pypopquiz as ppq
import pypopquiz.backends.backend
import pypopquiz.io


class FFMpeg(ppq.backends.backend.Backend):
    """FFMPEG backend, implements interface from base-class"""

    def __init__(self, source_file: Path, has_video: bool, has_audio: bool,
                 width: int, height: int, display_graph: bool = False, **kwargs: Any) -> None:
        super().__init__(has_video, has_audio, width, height)
        stream = ffmpeg.input(str(source_file), **kwargs)
        self.display_graph = display_graph
        self.stream_v = stream["v"] if self.has_video else None
        self.stream_a = stream["a"] if self.has_audio else None
        self.version = ffmpeg_version()

    def trim(self, start_s: int, end_s: int) -> None:
        """Trims a stream to a given start and end time measured in seconds"""
        if self.has_video:
            self.stream_v = self.stream_v.trim(start=start_s, end=end_s).filter("setpts", "PTS-STARTPTS")
        if self.has_audio:
            self.stream_a = self.stream_a.filter("atrim", start=start_s, end=end_s).filter("asetpts", "PTS-STARTPTS")

    def repeat(self) -> None:
        """Concatenates streams with itself to make a twice as long stream"""
        if self.has_video:
            stream_v = self.stream_v.split()
            joined = ffmpeg.concat(stream_v[0].filter("fifo"), stream_v[1].filter("fifo"), v=1, a=0).node
            self.stream_v = joined[0]
        if self.has_audio:
            stream_a = self.stream_a.asplit()
            joined = ffmpeg.concat(stream_a[0].filter("afifo"), stream_a[1].filter("afifo"), v=0, a=1).node
            self.stream_a = joined[0]

    def combine(self, other: 'FFMpeg', other_first: bool = False) -> None:  # type: ignore
        """Combines this stream with another stream"""
        first_stream = other if other_first else self
        second_stream = self if other_first else other
        if self.has_video:
            joined = ffmpeg.concat(first_stream.stream_v.filter("fifo"),
                                   second_stream.stream_v.filter("fifo"), v=1, a=0).node
            self.stream_v = joined[0]
        if self.has_audio:
            joined = ffmpeg.concat(first_stream.stream_a.filter("afifo"),
                                   second_stream.stream_a.filter("afifo"), v=0, a=1).node
            self.stream_a = joined[0]

    def fade_in_and_out(self, duration_s: int, video_length_s: int) -> None:
        """Adds a fade-in and fade-out to/from black for the audio and video stream"""
        if self.has_video:
            stream_v = self.stream_v.filter("fade", type="in", start_time=0, duration=duration_s)
            self.stream_v = stream_v.filter("fade", type="out", start_time=video_length_s - duration_s,
                                            duration=duration_s)
        if self.has_audio:
            stream_a = self.stream_a.filter("afade", type="in", start_time=0, duration=duration_s)
            self.stream_a = stream_a.filter("afade", type="out", start_time=video_length_s - duration_s,
                                            duration=duration_s)

    def scale_video(self) -> None:
        """Scales the video and pads if necessary to the requested dimensions"""
        if not self.has_video:
            return
        width = self.width
        height = self.height
        stream_v = self.stream_v.filter("scale", width=width, height=height, force_original_aspect_ratio=1)
        stream_v = stream_v.filter("pad", width=width, height=height, x="(ow-iw)/2", y="(oh-ih)/2", color="black")
        self.stream_v = stream_v.filter("setsar", sar="1/1")

    def draw_text_in_box(self, video_text: str, length: int, move: bool, top: bool) -> None:
        """Draws a semi-transparent box either at the top or bottom and writes text in it, optionally scrolling by"""
        if not self.has_video:
            return
        width = self.width
        height = self.height
        box_height = self.get_box_height()
        y_location = 0 if top else height - box_height

        thickness = "fill" if self.version.startswith("N") else "max"  # Assume nightlies are new.
        stream_v = self.stream_v.drawbox(x=0, y=y_location, width=width, height=box_height, color="gray@0.5",
                                         thickness=thickness)
        x_location_text = "{:d} * t / {:d}".format(width, length) if move else "{:d} - text_w / 2".format(width // 2)
        y_location_text = int(box_height * 1 / 4) if top else int(height - box_height * 3 / 4)
        self.stream_v = stream_v.drawtext(text=video_text, fontcolor="white", fontsize=self.get_font_size(),
                                          x=x_location_text, y=y_location_text)

    def draw_text(self, video_text: str, height_fraction: float) -> None:
        """Draws text in the center of the video at a certain height fraction"""
        if not self.has_video:
            return
        assert 0 <= height_fraction <= 1

        x_location_text = "{:d} - text_w / 2".format(self.width // 2)
        y_location_text = self.height * height_fraction
        self.stream_v = self.stream_v.drawtext(text=video_text, fontcolor="white", fontsize=self.get_font_size(),
                                               x=x_location_text, y=y_location_text)

    def add_audio(self, other: 'FFMpeg') -> None:  # type: ignore
        """Adds audio to this video clip from another source"""
        assert self.has_video and other.has_audio
        self.stream_a = other.stream_a
        self.has_audio = True

    def add_spacer(self, text: str, duration_s: float) -> None:
        """Add a text spacer to the start of the video clip."""
        assert self.has_video
        spacer = self.create_empty_stream(int(duration_s), self.width, self.height)
        spacer.draw_text_in_box(text, length=int(duration_s), move=True, top=False)
        self.combine(spacer, other_first=True)

    def add_silence(self, duration_s: float) -> None:
        """Add a silence of a certain duration the an audio clip."""
        assert self.has_audio
        no_audio = Path(pkg_resources.resource_filename("resources", "no_audio.mp3"))
        silence = FFMpeg(no_audio, has_video=False, has_audio=True, width=self.width, height=self.height,
                         t=duration_s)
        self.combine(silence, other_first=True)

    def reverse(self) -> None:
        """Reverses an entire audio or video clip."""
        if self.has_video:
            self.stream_v = self.stream_v.filter("reverse")
        if self.has_audio:
            self.stream_a = self.stream_a.filter("areverse")

    def run(self, file_name: Path, dry_run: bool = False) -> Path:
        """Runs the ffmpeg command to create the video, applying all the filters"""
        with FFMpeg.tmp_intermediate_file(file_name) as tmp_out:
            streams = []
            if self.has_video:
                streams.append(self.stream_v)
            if self.has_audio:
                streams.append(self.stream_a)
            output_stream = ffmpeg.output(*streams, str(tmp_out))
            if self.display_graph:
                output_stream.view(filename="ffmpeg_graph")  # optional visualisation of the graph
            if not dry_run:
                ppq.io.log("Running ffmpeg...")
                ppq.io.log("")
                output_stream.run()
                ppq.io.log("")
                ppq.io.log("Completed ffmpeg, successfully generated result")

        return file_name

    @classmethod
    def create_empty_stream(cls, duration: int, width: int, height: int) -> 'FFMpeg':
        """Creates a video of a certain duration with a black still image"""
        still_image = pkg_resources.resource_filename("resources", "still_black.png")
        return cls.create_single_image_stream(Path(still_image), duration, width=width, height=height)

    @classmethod
    def create_single_image_stream(cls, input_image: Path, duration: int,
                                   width: int, height: int) -> 'FFMpeg':
        """Creates a video of a certain duration with a single still image"""
        stream = cls(input_image, has_video=True, has_audio=False, width=width, height=height,
                     t=duration, framerate=25, loop=1)
        stream.scale_video()
        return stream


def ffmpeg_version() -> str:
    """Determine the ffmpeg version.

    Parses a line that looks like:
    "ffmpeg version N-91586-g90dc584d21 Copyright (c) 2000-2018 the FFmpeg developers"
    """
    res = None
    try:
        res = subprocess.check_output(['ffmpeg', '-version'])  # type: ignore
        # Need ignore, capture_output argument is not known to linter
    except subprocess.CalledProcessError:
        pass

    if res is None:
        raise RuntimeError("ffmpeg is probably not in the path.")

    version_str = res.decode('ascii').splitlines()[0]
    prefix = 'ffmpeg version '
    if not version_str.startswith(prefix):
        raise RuntimeError("Cannot parse ffmpeg version string.")

    # From here on, version string is assumed to be formatted as expected
    version_str = version_str[len(prefix):]
    version_chopped = version_str.split(' Copyright')[0]

    return version_chopped
