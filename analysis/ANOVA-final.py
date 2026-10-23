# Run whole-brain ANOVA cluster tests on source estimates.

import os, sys
import numpy as np
import mne
from pylab import *
import eelbrain as e
from functools import reduce
import operator
from pathlib import Path


e.configure(n_workers=True, prompt_toolkit="eelbrain")


# ---------------#
# Paths
# ---------------#

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from project_config import get_path
from helperfunctions import get_hemis, get_subj_group

main_dir = get_path("project_root")
data_dir = get_path("data")
mri_dir = get_path("mri")
meg_dir = get_path("meg")
stc_dir = get_path("stc")
log_dir = get_path("logs")

os.chdir(data_dir)

# ---------------#
# Settings
# ---------------#

# Analysis settings

subjects = [d for d in os.listdir(meg_dir) if "R" in d and ".md" not in d]

conditions = [
    i for i in os.listdir(stc_dir) if i.__contains__("_")
]  # this creates a list with the condition names from the stc dir
if len(conditions) != 6:
    conditions = conditions[:-1]
speeds = ["slow", "fast"]
print(conditions)

# ---------------#
# Script
# ---------------#

"""
# Get ROI
"""

# get whole brain and hemispheres
WB, LH, RH = get_hemis(mri_dir)

"""
### Create dataset
"""

# load stcs into a dataset with relevant info
subjectslist, conditionslist, stcs = [], [], []
for condition in conditions:
    for subject in subjects:
        filename = f"{stc_dir}/{condition}/{subject}_{condition}-sym_dSPM" 

        # load the stc
        stc = mne.read_source_estimate(filename, subject=subject)
        print(filename)
        stcs.append(stc)
        subjectslist.append(subject)
        conditionslist.append(condition)


# reads the different factors from the condition list
Structure = [str.split(i, "_")[0] for i in conditionslist]
Speed = [str.split(i, "_")[1] for i in conditionslist]

ds = e.Dataset()
# random effects
ds["Subject"] = e.Factor(subjectslist, random=True)  # within subj
ds["Group"] = e.Factor(
    [get_subj_group(log_dir, subj) for subj in ds["Subject"]], random=True
)
# fixed effects
ds["Structure"] = e.Factor(Structure)
ds["Speed"] = e.Factor(Speed)

ds["stcs"] = e.load.mne.stc_ndvar(stcs, "fsaverage_sym", "ico-4", mri_dir)
anova_dir = get_path("anova_results")
anova_dir.mkdir(parents=True, exist_ok=True)
e.save.pickle(ds, dest=anova_dir)

del stcs  # memory optimization; not really needed

"""
### Spatio-temporal test by speed
"""
full_contrast = "Structure * Subject"
contrast = "Structure"

roi_list = {"whole": WB}
speeds = ["slow", "fast"]

for speed in speeds:
    print(f"Starting {speed}")
    if speed == "fast":
        tmax = 0.45
    else:
        tmax = 0.8

    for name, roi in roi_list.items():
        # select results dir
        res_dir = get_path("anova_results") / name / speed
        res_dir.mkdir(parents=True, exist_ok=True)

        src = e.set_parc(
            ds["stcs"], "aparc.a2009s"
        )  # useful for the results table; we can also use APARC!

        ds["src"] = src
        # subset to region of interest
        
        # run the test
        res = e.testnd.ANOVA(
            ds["src"].sub(source=roi),
            x=full_contrast,
            ds=ds,
            sub=ds["Speed"] == speed,
            # samples=10000,  # number of permutations
            pmin=0.01,  # threshold for clusters (uncorrected p-value)
            tstart=0,  # start of the time window of interest
            tstop=tmax,  # stop of the time window of interest
            mintime=0.04,  # minimum duration for clusters
            minsource=40,  # minimum number of sources for clusters
            match="Subject",
        )  # makes it a within subject!!

        # save all results
        with open(res_dir / f"{contrast}_{name}results-{speed}-sym.npy", "wb") as f:
            np.save(f, res)
        res.clusters.sort("p")
        table = res.clusters.as_table()
        print(f"Results for {name}-{speed}", table)
        table.save_txt(
            res_dir / f"{contrast}-{name}__spatiotemporal_clusters-{speed}-sym.txt"
        )


