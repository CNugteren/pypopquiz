"""Abstract base class to define the video-editing interface"""

import abc
import contextlib
from pathlib import Path
import shutil
import tempfile
from typing import Generator, Tuple

import pypopquiz as ppq
import pypopquiz.io


class Backend(abc.ABC):
    """Abstract class to specify the backend interface"""

    def __init__(self, has_video: bool, has_audio: bool, width: int, height: int) -> None:
        self.has_video = has_video
        self.has_audio = has_audio
        self.width = width
        self.height = height

    def get_font_size(self) -> int:
        """Retrieves an appropriate font-size for this video"""
        return self.height // 14

    def get_box_height(self) -> int:
        """Retrieves an appropriate box-height for this video"""
        return self.height // 7

    @abc.abstractmethod
    def trim(self, start_s: int, end_s: int) -> None:
        """Trims a stream to a given start and end time measured in seconds"""
        pass

    @abc.abstractmethod
    def repeat(self) -> None:
        """Concatenates streams with itself to make a twice as long stream"""
        pass

    @abc.abstractmethod
    def combine(self, other: 'Backend') -> None:
        """Combines this stream with another stream"""
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
    def draw_text_in_box(self, video_text: str, length: int, move: bool, top: bool) -> None:
        """Draws a semi-transparent box either at the top or bottom and writes text in it, optionally scrolling by"""
        pass

    def draw_text(self, video_text: str, height_fraction: float) -> None:
        """Draws text in the center of the video at a certain height fraction"""
        pass

    @abc.abstractmethod
    def add_audio(self, other: 'Backend') -> None:  # type: ignore
        """Adds audio to this video clip from another source"""

    @abc.abstractmethod
    def run(self, file_name: Path, dry_run: bool = False) -> Path:
        """Runs the backend to create the video, applying all the filters"""
        pass

    @classmethod
    def create_empty_stream(cls, duration: int, width: int, height: int) -> 'Backend':
        """Creates a video of a certain duration with a black still image"""
        pass

    @classmethod
    def create_single_image_stream(cls, input_image: Path, duration: int,
                                   width: int, height: int) -> 'Backend':
        """Creates a video of a certain duration with a single still image"""
        pass

    def add_spacer(self, text: str, duration_s: float) -> None:
        """Add a text spacer to the start of the video clip."""
        pass

    def add_silence(self, duration_s: float) -> None:
        """Add a silence of a certain duration the an audio clip."""
        pass

    def reverse(self) -> None:
        """Reverses an entire audio or video clip."""
        pass

    def replace_audio_by_beep(self, interval: Tuple[float, float], freq_hz: int = 1500) -> None:
        """Replace the original audio by a beep in a particular interval."""
        pass

    def overlay_fading_text(self, text: str, interval: Tuple[float, float]):
        """Overlay fading text on the clip."""
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
                shutil.copy(str(tmp_out), str(file_name_out))
