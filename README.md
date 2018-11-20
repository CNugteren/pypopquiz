PyPopQuiz: A Python/ffmpeg-based popquiz creator
================

[![Build Status](https://travis-ci.org/CNugteren/pypopquiz.svg?branch=master)](https://travis-ci.org/CNugteren/pypopquiz/branches)

PyPopQuiz is still under development, head back soon if you are looking for a fully working tool. If you are a developer, you can already start testing the tool. You can install it using `pip install -e .` and then run the tool, e.g.:

    popquiz.py -i samples/round01.json -o output_folder

To use the moviepy backend, add `-b moviepy` to the command line.

Requirements
-------------

Tested on Linux. Requires Python 3.5 or newer. Requires ffmpeg and the Python packages `pytube` and `ffmpeg-python` or `moviepy`, installed as part of the requirements.


Tests
-------------

The tests are currently still quite limited, but you can already run the linters and/or unittests, e.g. from the root:

    pylint pypopquiz test
    mypy pypopquiz --ignore-missing-imports
    python -m unittest discover test


Feature list / roadmap
-------------

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
