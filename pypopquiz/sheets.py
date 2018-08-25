"""Module to generate output question/answer sheets for printing"""

from pathlib import Path
from typing import Dict

import pypopquiz as ppq
import pypopquiz.io


def create_sheets(kind: str, input_data: Dict, output_dir: Path, table_width: int = 40) -> None:
    """Creates a question or answer sheet for printing in Markdown format"""
    assert kind in ["question", "answer"]
    ppq.io.log("Generating {:s} sheets for round {:02d}".format(kind, input_data["round"]))

    # The file header
    contents = list()
    contents.append("Round {:02d}: {:s}".format(input_data["round"], input_data["theme"]))
    contents.append("================")
    contents.append("")

    # The table header
    header = "| {:10s} |".format("Question")
    spacer = "|-{:10s}-|".format("-" * 10)
    for questioned in input_data["questioned"]:
        header += " {:40s} |".format(questioned)
        spacer += "-{:40s}-|".format("-" * table_width)
    contents.append(header)
    contents.append(spacer)

    # The table contents
    for index, question in enumerate(input_data["questions"]):
        question_id = "{:d}.{:d}".format(input_data["round"], index + 1)
        table_line = ("| {:10s} |".format(question_id))
        for questioned in input_data["questioned"]:
            field = ""
            for sub_question in question["answers"]:
                if kind == "answer" and questioned in sub_question:
                    field = sub_question[questioned]
            table_line += " {:40s} |".format(field)
        contents.append(table_line)

    # Output to disk as Markdown
    file_name = output_dir / ("{:02d}_{:s}.md".format(input_data["round"], kind))
    ppq.io.log("Storing {:s} sheets to {:s}".format(kind, str(file_name)))
    ppq.io.write_lines(contents, file_name)
