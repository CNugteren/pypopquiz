"""Main entry point for the pypopquiz package"""

import argparse
from pathlib import Path

import pypopquiz as ppq
import pypopquiz.io
import pypopquiz.sheets
import pypopquiz.sources
import pypopquiz.video


def parse_arguments():
    """Sets the command-line arguments"""
    parser = argparse.ArgumentParser(description="pypopquiz interface")
    parser.add_argument("-i", "--input_file", required=True, help="Input JSON file with popquiz info", type=Path)
    parser.add_argument("-o", "--output_dir", required=True, help="Output dir with popquiz data", type=Path)
    parser.add_argument("-b", "--backend", required=False, help="Backend selection (ffmpeg or moviepy)",
                        type=str, default='ffmpeg')
    parser.add_argument("-d", "--downloader", required=False, help="Downloader selection (pytube or youtube-dl)",
                        type=str, default='pytube')
    parser.add_argument("--width", required=False, help="Video width", type=int, default=1280)
    parser.add_argument("--height", required=False, help="Video height", type=int, default=720)
    return vars(parser.parse_args())


def popquiz(input_file: Path, output_dir: Path, backend: str, downloader: str, width: int, height: int,
            title_text_duration_s: int = 10) -> None:
    """The main routine, constructing the entire popquiz output"""

    input_data = ppq.io.read_input(input_file)
    round_id = input_data["round"]
    questioned = input_data["questioned"]
    ppq.io.log("Processing popquiz round {:d}".format(round_id))

    round_dir = output_dir / ("{:02d}".format(round_id))
    if not round_dir.exists():
        round_dir.mkdir()

    spacer_txt = input_data.get('spacers', '')
    use_cached_video_files = input_data.get('use_cached_video_files', False)
    first_question_is_example = input_data.get('first_question_is_example', False)

    for question in input_data["questions"]:
        for source in question["sources"]:
            ppq.sources.get_source(source, output_dir, input_file.parent, width=width, height=height,
                                   backend=backend, downloader=downloader)

    theme = '"{:s}"'.format(input_data["theme"])
    q_title = ppq.video.create_text_video(round_dir / ("{:02d}_questions_title.mp4".format(round_id)),
                                          ["Round {:02d}".format(round_id), theme],
                                          title_text_duration_s, width=width, height=height,
                                          use_cached_video_files=use_cached_video_files, backend=backend)
    a_title = ppq.video.create_text_video(round_dir / ("{:02d}_answers_title.mp4".format(round_id)),
                                          ["Answers for round {:02d}".format(round_id), theme],
                                          title_text_duration_s, width=width, height=height,
                                          use_cached_video_files=use_cached_video_files, backend=backend)

    q_videos, a_videos = [q_title], [a_title]
    for index, question in enumerate(input_data["questions"]):
        question_id = index + int(not first_question_is_example)  # start with 0 when having an example
        is_example = first_question_is_example and index == 0

        answer_texts = []
        for answers in question["answers"]:
            answer_texts.append([answers[question_text] for question_text in questioned if question_text in answers])

        ppq.io.log("Processing question {:d}: {:s}".format(question_id, str(answer_texts)))
        q_video = ppq.video.create_video("question", round_id, question, question_id, output_dir, round_dir,
                                         answer_texts, width=width, height=height, backend=backend,
                                         spacer_txt=spacer_txt, use_cached_video_files=use_cached_video_files,
                                         is_example=is_example)
        a_video = ppq.video.create_video("answer", round_id, question, question_id, output_dir, round_dir,
                                         answer_texts, width=width, height=height, backend=backend,
                                         spacer_txt=spacer_txt, use_cached_video_files=use_cached_video_files,
                                         is_example=is_example)
        q_videos.append(q_video)
        if is_example:
            q_videos.append(a_video)  # show the answer of the example directly after the example question
        else:
            a_videos.append(a_video)

    ppq.video.combine_videos(q_videos, "question", round_id, output_dir, backend=backend, width=width, height=height)
    if a_videos:
        ppq.video.combine_videos(a_videos, "answer", round_id, output_dir, backend=backend, width=width, height=height)

    ppq.sheets.create_sheets("question", input_data, output_dir)
    ppq.sheets.create_sheets("answer", input_data, output_dir)


if __name__ == "__main__":
    popquiz(**parse_arguments())
