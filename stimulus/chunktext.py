#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This script chunks a text file into largest constituents adding a character limit to each chunk
# Run this and then edits chunks for clarity before running logcreator.py to create the stimulus csv files

import argparse
import csv
import sys
from pathlib import Path

import stanza

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from project_config import get_path


def extract_largest_constituents_char(sentence,char_lim):
    chunks = []
    current_chunk = []
    current_length = 0  # Track character count

    for word in sentence.words:
        word_text = word.text
        word_length = len(word_text) + 1  # Account for spaces

        if word.head == 0:  # Root of sentence (main verb)
            if current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_length = 0

        # If adding the word exceeds 23 characters, start a new chunk
        if current_length + word_length > char_lim and current_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_length = 0

        current_chunk.append(word_text)
        current_length += word_length

    if current_chunk:
        chunks.append(" ".join(current_chunk))  # Add last chunk

    return chunks


# Read chunked text file and process lines
def process_chunked_text(file_path, output_csv_path, nlp):
    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()

    # Using CSV module to create a log file
    output_csv_path = Path(output_csv_path)
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_csv_path, "w", newline="", encoding="utf-8") as csv_file:
        csv_writer = csv.writer(csv_file, delimiter='\t', lineterminator='\n')
        csv_writer.writerow(["chunk"])


        chunk_number = 1
        for line in lines:
            if not line.strip():  # Empty line indicates a new paragraph
                csv_writer.writerow([])  # Write an empty line in CSV
                continue

            doc = nlp(line.strip())  # Process line with Stanza

            # Extract largest constituents
            for sentence in doc.sentences:
                chunks = extract_largest_constituents_char(sentence, 23)
                for chunk in chunks:
                    # Write to CSV
                    csv_writer.writerow([chunk])
                    chunk_number += 1

    print(f"\nProcessing completed. CSV written to {output_csv_path}")



def main(argv=None):
    """Chunk a story text file and write tab-separated chunks."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path, default=get_path("stimuli") / "story1.txt"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=get_path("stimuli") / "story1_chunked.tsv",
    )
    args = parser.parse_args(argv)
    if not args.input.is_file():
        parser.error(f"Input text file does not exist: {args.input}")

    nlp = stanza.Pipeline(lang="en", processors="tokenize,pos,lemma,depparse")
    process_chunked_text(args.input, args.output, nlp)


if __name__ == "__main__":
    main()