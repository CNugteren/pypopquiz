PyPopQuiz: A Python/ffmpeg-based popquiz creator
================

[![Build Status](https://travis-ci.org/CNugteren/pypopquiz.svg?branch=master)](https://travis-ci.org/CNugteren/pypopquiz/branches)

PyPopQuiz is still under development, head back soon if you are looking for a fully working tool. If you are a developer, you can already start testing the tool. You can install it using `pip install -e .` and then run the tool, e.g.:

    popquiz.py -i samples/round01.json -o output_folder

To use the moviepy backend, add `-b moviepy` to the command line.

Requirements
-------------

Tested on Linux. Requires Python 3.5 or newer. Requires ffmpeg and the Python packages `ffmpeg-python` and `pytube`, installed as part of the requirements.


Tests
-------------

The tests are currently still quite limited, but you can already run the linters and/or unittests, e.g. from the root:

    pylint pypopquiz test
    mypy pypopquiz --ignore-missing-imports
    python -m unittest discover test


Feature list / roadmap
-------------

| Feature | Status |
|---------|--------|
| Read JSON input | ✔ |
| Download YouTube sources | ✔ |
| Create question video | in progress |
| Create answers video | in progress |
| Support audio only rounds |  |
| Support video only rounds |  |
| Support text-only rounds |  |
| Support reversed video |  |
| Support audio and video from different sources |  |
| Support 8-bit audio rounds |  |
| Support missing-word/beep rounds |  |
