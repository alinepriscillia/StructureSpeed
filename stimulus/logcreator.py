# This script creates a stimulus logfile with relevant metadata for each chunk of a story
# Stimulus text needs to have paragraphs indented before the script is run to create the stimulus csv file
# Run this after running chunktext.py to create the chunked text file, which is then used as input for this script

import argparse
import csv
import sys
from pathlib import Path

import stanza

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from project_config import get_path


# define the set of content word POS tags, subject to change if needed
content_word_tags = {'NN', 'NNS', 'NNP', 'NNPS',  # Nouns
                     'VB', 'VBD', 'VBG', 'VBN',  # Verbs
                     'JJ',  # Adjectives
                     'RB'}  # Adverbs

# function to use stanza on each chunk, and return the content words and number by going through each word in sentence and seeing if it is in the pos list
def process_chunk(chunk, stanza_nlp):
    doc = stanza_nlp(chunk)
    content_words = []

    for sentence in doc.sentences:
        for word in sentence.words:
            if word.xpos in content_word_tags:
                content_words.append(word.text)  # append the actual word text
                #print(content_words)

    return len(content_words), content_words
# determines paragraph number by checking if theres an empty line, then adding paragraph +1 if so
def determine_paragraph_number(lines):
    paragraph_numbers = []
    paragraph_counter = 1

    for line in lines:
        if not line.strip():  # Empty line indicates a new paragraph
            paragraph_counter += 1
        paragraph_numbers.append(paragraph_counter)

    return paragraph_numbers

# read chunked texr file and separate into lines as needed
def process_chunked_text(file_path, output_csv_path, nlp):
    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()

    # determine paragraph numbers
    paragraph_numbers = determine_paragraph_number(lines)
    chunk_number = 1
    # using csv module to create a log file; now a tsv file to save the punctuation
    output_csv_path = Path(output_csv_path)
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    sentence_counter = 1
    with open(output_csv_path, "w", newline="", encoding="utf-8") as csv_file:
        csv_writer = csv.writer(csv_file, delimiter='\t', lineterminator='\n')
        # write the header row of columns
        csv_writer.writerow(
            ["chunk", "cnum", "clen", "pnum", "snum", "numcontentw", "contentw"]
        )

        # use the chunk processing script on each line (chunk)
        for i, line in enumerate(lines):
            chunk = line.strip()
            #print(chunk)
            paragraph_number = paragraph_numbers[i]

            # skip empty lines (paragraph separators)
            if not chunk:
                continue

            # process the chunk to get content words and their count
            num_content_words, content_words = process_chunk(chunk, nlp)

            sentence_number = sentence_counter
            sentence_counter += sum(chunk.count(mark) for mark in ".!?")
            chunk_number += 1
            # write all the results to CSV file and done
            csv_writer.writerow(
                [
                    chunk,
                    chunk_number,
                    len(chunk),
                    paragraph_number,
                    sentence_number,
                    num_content_words,
                    ", ".join(content_words),
                ]
            )
    print(f"\n Processing completed. CSV written to {output_csv_path}")


def main(argv=None):
    """Create a stimulus log with sentence, paragraph, and content-word metadata."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path, default=get_path("stimuli") / "story3_chunked.tsv"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=get_path("stimuli") / "story3_final_stim.tsv",
    )
    args = parser.parse_args(argv)
    if not args.input.is_file():
        parser.error(f"Input chunk file does not exist: {args.input}")

    nlp = stanza.Pipeline("en", processors="tokenize,pos")
    process_chunked_text(args.input, args.output, nlp)


if __name__ == "__main__":
    main()
