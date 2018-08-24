"""Main entry point for the pypopquiz package"""

import argparse
from pathlib import Path

import pypopquiz as ppq
import pypopquiz.io
import pypopquiz.sheets
import pypopquiz.video


def parse_arguments():
    """Sets the command-line arguments"""
    parser = argparse.ArgumentParser(description="pypopquiz interface")
    parser.add_argument("-i", "--input_file", required=True, help="Input JSON file with popquiz info", type=Path)
    parser.add_argument("-o", "--output_dir", required=True, help="Output dir with popquiz data", type=Path)
    parser.add_argument("-b", "--backend", required=False, help="Backend selection", type=str, default='ffmpeg')
    return vars(parser.parse_args())


def popquiz(input_file: Path, output_dir: Path, backend: str) -> None:
    """The main routine, constructing the entire popquiz output"""

    input_data = ppq.io.read_input(input_file)
    round_id = input_data["round"]
    ppq.io.log("Processing popquiz round {:d}".format(round_id))

    spacer_txt = input_data.get('spacers', '')
    use_cached_video_files = input_data.get('use_cached_video_files', False)
    first_question_is_example = input_data.get('first_question_is_example', False)

    for question in input_data["questions"]:
        for source in question["sources"]:
            ppq.io.get_source(source, output_dir, input_file.parent)

    q_videos, a_videos = [], []
    for index, question in enumerate(input_data["questions"]):
        question_id = index + int(not first_question_is_example)  # start with 0 when having an example
        is_example = first_question_is_example and index == 0

        ppq.io.log("Processing question {:d}".format(question_id))
        q_video = ppq.video.create_video("question", round_id, question, question_id, output_dir,
                                         backend=backend, spacer_txt=spacer_txt,
                                         use_cached_video_files=use_cached_video_files, is_example=is_example)
        a_video = ppq.video.create_video("answer", round_id, question, question_id, output_dir,
                                         backend=backend, spacer_txt=spacer_txt,
                                         use_cached_video_files=use_cached_video_files, is_example=is_example)
        q_videos.append(q_video)
        if is_example:
            q_videos.append(a_video)  # show the answer of the example directly after the example question
        else:
            a_videos.append(a_video)

    ppq.video.combine_videos(q_videos, "question", round_id, output_dir, backend=backend)
    if a_videos:
        ppq.video.combine_videos(a_videos, "answer", round_id, output_dir, backend=backend)

    ppq.sheets.create_sheets("question", input_data, output_dir)
    ppq.sheets.create_sheets("answer", input_data, output_dir)


if __name__ == "__main__":
    popquiz(**parse_arguments())
