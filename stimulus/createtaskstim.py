#!/usr/bin/env python3
"""Create task stimulus sheets by sampling chunks from the story files."""

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from project_config import get_path


def sample_story(story, sample_size, match, random_state):
    """Return a random, labeled sample from one story table."""
    if "chunk" not in story:
        raise ValueError("Each stimulus file must contain a 'chunk' column.")
    if len(story) < sample_size:
        raise ValueError(
            f"Expected at least {sample_size} rows to sample, found {len(story)}."
        )
    sample = story.sample(n=sample_size, random_state=random_state).copy()
    sample["match"] = match
    return sample


def main(argv=None):
    """Load story stimuli, sample task sheets, and save them to the task folder."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    stimuli_dir = get_path("stimuli")
    story1 = pd.read_csv(stimuli_dir / "story1_final_stim.tsv", sep="\t")
    story2 = pd.read_csv(stimuli_dir / "story2_final_stim.tsv", sep="\t")
    story3 = pd.read_csv(stimuli_dir / "story3_final_stim.tsv", sep="\t")

    story1_sample_2 = sample_story(story1, 15, False, args.seed)
    story1_sample_3 = sample_story(story1, 15, False, args.seed + 1)
    story2_sample = sample_story(story2, 15, True, args.seed + 2)
    story3_sample = sample_story(story3, 15, True, args.seed + 3)

    story2_task = pd.concat([story2_sample, story1_sample_2], ignore_index=True)
    story3_task = pd.concat(
        [story3_sample, story1_sample_3], ignore_index=True
    ).drop(columns=["answer1", "answer2", "answer_correct", "question"], errors="ignore")

    task_dir = get_path("stimulus_task")
    task_dir.mkdir(parents=True, exist_ok=True)
    story2_task.to_csv(task_dir / "story2_task_stim.tsv", sep="\t", index=False)
    story3_task.to_csv(task_dir / "story3_task_stim.tsv", sep="\t", index=False)


if __name__ == "__main__":
    main()
