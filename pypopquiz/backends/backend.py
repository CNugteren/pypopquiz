"""Abstract base class to define the video-editing interface"""

import abc
import contextlib
from pathlib import Path
import shutil
import tempfile
from typing import Generator

import pypopquiz as ppq
import pypopquiz.io



class Backend(abc.ABC):
    """Abstract class to specify the backend interface"""

    def __init__(self, width: int = 1280, height: int = 720) -> None:
        self.width = width
        self.height = height

    @abc.abstractmethod
    def trim(self, start_s: int, end_s: int) -> None:
        """Trims a video to a given start and end time measured in seconds"""
        pass

    @abc.abstractmethod
    def repeat(self) -> None:
        """Concatenates a video and audio stream with itself to make a twice as long video"""
        pass

    def combine(self, other: 'Backend') -> None:
        """Combines this video stream with another stream"""
        pass

    @abc.abstractmethod
    def fade_in_and_out(self, duration_s: int, video_length_s: int) -> None:
        """Adds a fade-in and fade-out to/from black for the audio and video stream"""
        pass

    @abc.abstractmethod
    def scale_video(self) -> None:
        """Scales the video and pads if necessary to the requested dimensions"""
        pass

    @abc.abstractmethod
    def draw_text_in_box(self, video_text: str, length: int, box_height: int, move: bool, top: bool) -> None:
        """Draws a semi-transparent box either at the top or bottom and writes text in it, optionally scrolling by"""
        pass

    @abc.abstractmethod
    def run(self, file_name: Path, dry_run: bool = False) -> Path:
        """Runs the backend to create the video, applying all the filters"""
        pass

    def add_spacer(self, text: str, duration_s: float) -> None:
        """Add a text spacer to the start of the clip."""
        pass

    @staticmethod
    @contextlib.contextmanager
    def tmp_intermediate_file(file_name_out: Path) -> Generator[Path, None, None]:
        """Create a temporary intermediate file and copy to destination after body completes."""
        with tempfile.TemporaryDirectory() as tmpdirname:
            ppq.io.log('Created temporary directory {}'.format(tmpdirname))
            tmp_out = Path(tmpdirname) / file_name_out.name

            yield tmp_out

            if tmp_out.exists():
                # Use shutil.copy, since Path.rename does not work across drives:
                ppq.io.log('Copy result to {}'.format(file_name_out))
                shutil.copy(str(tmp_out), file_name_out)
