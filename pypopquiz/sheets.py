"""Module to generate output question/answer sheets for printing"""

from pathlib import Path
from typing import Dict

import pypopquiz as ppq
import pypopquiz.io


def create_sheets(kind: str, input_data: Dict, output_dir: Path, table_width: int = 40) -> None:
    """Creates a question or answer sheet for printing in Markdown format"""
    assert kind in ["question", "answer"]

    # The file header
    contents = list()
    contents.append("Round {:02d}: {:s}".format(input_data["round"], input_data["theme"]))
    contents.append("================")
    contents.append("")

    # The table header
    contents.append("| {:10s} | {:40s} | {:40s} |".format("Question", "Artist", "Title"))
    contents.append("|-{:10s}-|-{:40s}-|-{:40s}-|".format("-" * 10, "-" * table_width, "-" * table_width))

    # The table contents
    for index, question in enumerate(input_data["questions"]):
        field1 = question["artist"] if kind == "answer" else ""
        field2 = question["title"] if kind == "answer" else ""
        question_id = "{:d}.{:d}".format(input_data["round"], index + 1)
        contents.append("| {:10s} | {:40s} | {:40s} |".format(question_id, field1, field2))

    # Output to disk as Markdown
    file_name = output_dir / ("{:02d}_{:s}.md".format(input_data["round"], kind))
    ppq.io.write_lines(contents, file_name)
