"""FFMPEG backend for video editing"""

from pathlib import Path
import subprocess

import ffmpeg

import pypopquiz as ppq
import pypopquiz.backends.backend
import pypopquiz.io


class FFMpeg(ppq.backends.backend.Backend):
    """FFMPEG backend, implements interface from base-class"""

    def __init__(self, source_file: Path, display_graph: bool = False, width: int = 1280, height: int = 720) -> None:
        super().__init__(width, height)
        stream = ffmpeg.input(str(source_file))
        self.display_graph = display_graph
        self.stream_v = stream["v"]
        self.stream_a = stream["a"]
        self.version = ffmpeg_version()

    def trim(self, start_s: int, end_s: int) -> None:
        """Trims a video to a given start and end time measured in seconds"""
        self.stream_v = self.stream_v.trim(start=start_s, end=end_s).filter("setpts", "PTS-STARTPTS")
        self.stream_a = self.stream_a.filter("atrim", start=start_s, end=end_s).filter("asetpts", "PTS-STARTPTS")

    def repeat(self) -> None:
        """Concatenates a video and audio stream with itself to make a twice as long video"""
        stream_v = self.stream_v.split()
        stream_a = self.stream_a.asplit()
        joined = ffmpeg.concat(stream_v[0].filter("fifo"), stream_a[0].filter("afifo"),
                               stream_v[1].filter("fifo"), stream_a[1].filter("afifo"), v=1, a=1).node
        self.stream_v, self.stream_a = joined[0], joined[1]

    def combine(self, other: 'FFMpeg') -> None:  # type: ignore
        """Combines this video stream with another stream"""
        joined = ffmpeg.concat(self.stream_v.filter("fifo"), self.stream_a.filter("afifo"),
                               other.stream_v.filter("fifo"), other.stream_a.filter("afifo"), v=1, a=1).node
        self.stream_v, self.stream_a = joined[0], joined[1]

    def fade_in_and_out(self, duration_s: int, video_length_s: int) -> None:
        """Adds a fade-in and fade-out to/from black for the audio and video stream"""
        stream_v = self.stream_v.filter("fade", type="in", start_time=0, duration=duration_s)
        self.stream_v = stream_v.filter("fade", type="out", start_time=video_length_s - duration_s,
                                        duration=duration_s)
        stream_a = self.stream_a.filter("afade", type="in", start_time=0, duration=duration_s)
        self.stream_a = stream_a.filter("afade", type="out", start_time=video_length_s - duration_s,
                                        duration=duration_s)

    def scale_video(self) -> None:
        """Scales the video and pads if necessary to the requested dimensions"""
        width = self.width
        height = self.height
        stream_v = self.stream_v.filter("scale", width=width, height=height, force_original_aspect_ratio=1)
        self.stream_v = stream_v.filter("pad", width=width, height=height, x="(ow-iw)/2", y="(oh-ih)/2", color="black")

    def draw_text_in_box(self, video_text: str, length: int, box_height: int, move: bool, top: bool) -> None:
        """Draws a semi-transparent box either at the top or bottom and writes text in it, optionally scrolling by"""
        width = self.width
        height = self.height
        y_location = 0 if top else height - box_height

        thickness = "fill" if self.version.startswith("N") else "max"  # Assume nightlies are new.
        stream_v = self.stream_v.drawbox(x=0, y=y_location, width=width, height=box_height, color="gray@0.5",
                                         thickness=thickness)
        x_location_text = "{:d} * t / {:d}".format(width, length) if move else "{:d} - text_w / 2".format(width // 2)
        y_location_text = int(box_height * 1 / 4) if top else int(height - box_height * 3 / 4)
        self.stream_v = stream_v.drawtext(text=video_text, fontcolor="white", fontsize=50,
                                          x=x_location_text, y=y_location_text)

    def run(self, file_name: Path, dry_run: bool = False) -> Path:
        """Runs the ffmpeg command to create the video, applying all the filters"""
        output_stream = ffmpeg.output(self.stream_v, self.stream_a, str(file_name))
        if self.display_graph:
            output_stream.view(filename="ffmpeg_graph")  # optional visualisation of the graph
        if not dry_run:
            ppq.io.log("Running ffmpeg...")
            ppq.io.log("")
            output_stream.run()
            ppq.io.log("")
            ppq.io.log("Completed ffmpeg, successfully generated result")

        return file_name


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
