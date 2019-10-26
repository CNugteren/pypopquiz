# PyPopQuiz: A Python/ffmpeg-based popquiz creator

[![Build Status](https://travis-ci.org/CNugteren/pypopquiz.svg?branch=master)](https://travis-ci.org/CNugteren/pypopquiz/branches)

PyPopQuiz is a python package to generate popquiz-videos (questions and answers) based simple JSON files with descriptions of the quiz-questions. Such a JSON description could for example contain a song's title and answer which need to be guessed, along with a YouTube-link and two time-intervals defined for the audio and/or video question and answer. It includes features such as only audio, only video, combined audio and video, local files, YouTube links, reversed audio, text overlays, missing words rounds, and so on.

You can install it using `pip install -e .` and then run the tool, e.g.:

    popquiz.py -i samples/round01.json -o output_folder

To use the moviepy backend, add `-b moviepy` to the command line.

## Requirements

Tested on Linux and Windows. Requires Python 3.5 or newer. Requires ffmpeg and the Python packages `pytube` and `ffmpeg-python` or `moviepy`, installed as part of the requirements.

### Moviepy

On Windows: Set environment variables pointing to ffmpeg and imagemagick (convert) for moviepy to use:

`FFMPEG_BINARY=path_to_ffmpeg\ffmpeg.exe`

`IMAGEMAGICK_BINARY=path_to_imagemagick\convert.exe`

[Patch for no audio issue](https://github.com/Sv3n/moviepy/commit/130160de539bbdb0473bb2e994ed56a58f9f9ab0)

## Tests

The tests are currently still quite limited, but you can already run the linters and/or unittests, e.g. from the root:

    pylint pypopquiz test
    mypy pypopquiz --ignore-missing-imports
    python -m unittest discover test


## Feature list / roadmap

| Input/output                     | Status      |
|----------------------------------|-------------|
| Input source: Youtube video      | ✔           |
| Input source: Local mp3          | ✔           |
| Output: Questions video          | ✔           |
| Output: Answers video            | ✔           |
| Output: Question & answer sheets | ✔           |

| Types of rounds                | Status      |
|--------------------------------|-------------|
| Audio & video                  | ✔           |
| Audio only                     | ✔           |
| Text only round                |             |
| Beeps/gaps/missing-word round  | ✔           |

| Special features               | Status      |
|--------------------------------|-------------|
| Reversed audio & video         | ✔           |
| 8-bit/chiptunes audio          |             |
