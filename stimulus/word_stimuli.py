# This script creates a scrambled version of the stories used in the final MEG experiment
# It takes as input the output from chunktext.py after manual editing steps. 
# The shuffling is done randomly without seed. 

import pandas as pd
import random
import copy
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from project_config import get_path

def main():
    """Create a shuffled stimulus table for a selected story."""
    stimuli_dir = get_path("stimuli")

    story_num = input("what number story? \n")
    # load the original CSV file as a pandas df
    input_csv_path = stimuli_dir / f"story{story_num}_final_stim.tsv"
    output_csv_path = stimuli_dir / f"story{story_num}_scrambled.csv"
    df = pd.read_csv(input_csv_path, delimiter='\t')

    output = pd.DataFrame()

    # get word lengths for speed manipulation calculation
    word_lengths = []
    for chunk in df["chunk"]:
        words = chunk.split()  # split the chunk into words
        n_words = len(words)
        word_lengths.append(n_words)
    df["n_words"] = word_lengths
    df[["n_words", "chunk"]].to_csv(
        stimuli_dir / f"story{story_num}-chunk+words.csv", index=False
    )

    # get max chunks
    maxcnum = len(df["chunk"])
    # variable to create a pool of all words
    all_words = []

    # split every chunk, and then add the words in the chunk to the grand list, and create a list for
    # all the lengths of each chunk, which will be used to add words back in
    char_counts_per_chunk = []
    for chunk in df["chunk"]:
        words = chunk.split()  # split the chunk into words
        all_words.extend(words)  # add words to the list
        char_counts_per_chunk.append(len(chunk))  # add to a new list recording word length


    # shuffle all the words randomly
    random.shuffle(all_words)

    # create a deep copy to do sampling with replacement
    all_words2 = copy.deepcopy(all_words)
    random.shuffle(all_words2)

    start = 0
    resample = 0
    shuffled_chunks = []
    len_chunks = []

    # loop that goes through all of the chunks and tries to compose each chunk to be as long as the target chunk

    for i in range(maxcnum):
        tar_length = len(df["chunk"][i])  # get length of current chunk
        end = start + 1
        if end < len(all_words):
            shuffled_chunk = all_words[start]  # subset to starting chunk
            #end = start + 1  # Next word index
            while len(shuffled_chunk) < tar_length and end < len(all_words):
                new_chunk = shuffled_chunk + " " + all_words[end]
                if len(new_chunk) > 23:  # Stop if adding another word exceeds limit
                    break
                shuffled_chunk = new_chunk  # Otherwise, accept the new chunk
                end += 1

            start = end
        else:  # once we reach the end of the text sample from shuffled list again
            shuffled_chunk = all_words2[resample]  # subset to starting chunk
            end = resample + 1  # Next word index; reset at end of text
            while len(shuffled_chunk) < tar_length and end < len(all_words2):
                new_chunk = shuffled_chunk + " " + all_words2[end]
                if len(new_chunk) > 23:  # Stop if adding another word exceeds limit
                    break
                shuffled_chunk = new_chunk  # Otherwise, accept the new chunk
                end += 1
            resample = end

        shuffled_chunks.append(shuffled_chunk)
        lenshuff = len(shuffled_chunk)
        len_chunks.append(lenshuff)


    print("This is the number of repeated words:", resample)
    # update the DataFrame with the shuffled chunks and chunk numbers again
    output["chunk"] = shuffled_chunks
    output["cnum"] = range(1, maxcnum + 1)
    output["clen"] = len_chunks

    # write back into a csv file
    output.to_csv(output_csv_path, index=False)

    print(f"Shuffled words across all chunks CSV written to {output_csv_path}")


if __name__ == "__main__":
    main()
