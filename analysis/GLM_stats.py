# This script runs group-level statistics and cluster plots for saved GLM results.

import os, sys
import numpy as np
import mne
from pylab import *
import eelbrain as e
from functools import reduce
from pathlib import Path
from matplotlib.colors import to_rgba
import argparse
import re




# ---------------#
# Paths
# ---------------#

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from project_config import get_path
from helperfunctions import (
    get_subj_group,
    get_vertices_list,
    get_froi_res,
    ClusterPlotter,
)

def clean_regressor_labels(reg_labels):
    """
    Clean up patsy-generated regressor labels for readability.
    - Replace 'C(condition)[T.cond]' with 'cond'
    - Handle interactions like 'C(condition)[T.cond]:trl_scaled_centered' as 'cond:trl_scaled_centered'
    - Keep 'Intercept' and other non-categorical labels as-is
    """
    clean_labels = []
    for label in reg_labels:
        if 'C(condition)[T.' in label:
            # Extract the condition name from the dummy
            cond = label.split('[T.')[1].split(']')[0]
            if ':' in label:
                # Interaction term
                clean_labels.append(f"{cond}:trl_scaled")
            else:
                # Main effect
                clean_labels.append(cond)
        elif label == 'Intercept':
            clean_labels.append('Intercept')
        else:
            # Other continuous variables
            clean_labels.append(label)
    return clean_labels

def process_subject(subj,speed, res_dir, mri_dir, fs):
    """Load one subject's GLM results and return morphed estimates by regressor.

    Args:
        subj: Subject identifier.
        speed: Speed condition used to select the saved regression results.
        res_dir: Directory containing the subject's regression results.
        mri_dir: FreeSurfer subjects directory used for morphing.
        fs: Sampling frequency used to set the source-estimate time step.

    Returns:
        A dictionary mapping cleaned regressor labels to morphed MNE estimates.
    """
    vertices_list = get_vertices_list(subj, mri_dir)
    resfname = f"{subj}-allconds_{speed}-regressionresults.npy" # new res fname

    vals = np.load(res_dir / resfname, allow_pickle=True).item()
    
    reg_labels = vals["reg_labels"]
    clean_labels = clean_regressor_labels(reg_labels)

    b_map = vals["beta"]
    
    stcs = {}
    for i, label in enumerate(clean_labels):
        stc = mne.SourceEstimate(
            data=b_map[:, :, i],
            vertices=vertices_list,
            tmin=0, tstep=1/fs, subject=subj
        )
        # morph the subject if needed
        morph = mne.compute_source_morph(
            stc, subject_from=subj, subject_to="fsaverage_sym",
            subjects_dir=mri_dir, spacing=4
        )
        stcs[label] = morph.apply(stc)
        
    return stcs

parser = argparse.ArgumentParser(description="Run GLM stats across conditions")
parser.add_argument("--speed", nargs="+", required=True)
parser.add_argument("--res_dir", type=Path)
args = parser.parse_args()

e.configure(n_workers=True, prompt_toolkit="eelbrain")

PATH = get_path("project_root")
main_dir = get_path("data")
mri_dir = get_path("mri")
meg_dir = get_path("meg")
log_dir = get_path("logs")
res_dir = args.res_dir or get_path("glm_results")
os.chdir(PATH)

subjects = [d for d in os.listdir(meg_dir) if "R" in d and ".md" not in d]
colors = [
    "#EDBA7E",
    "#EFDDA9",
    "#CBCF7E",
    "#B0C885",
    "#F9C8D9",
    "#DAA6BA",
    "#A98CB2",
    "#74678E",
]
fs = 500
load_froi = False
region = "whole"
matplotlib.rcParams.update({"font.size": 10})
matplotlib.rcParams["font.family"] = "Arial"

# ---------------#
# Script
# ---------------#

""" ------------------ ROI ------------------ """
res_speed =  "slow"

if load_froi:
    # get fROI from the clusters
    region = "whole"
    clu_dir = get_path("anova_results") / region / res_speed

    contrast = "Structure"
    results = np.load(
        Path(clu_dir) / f"{contrast}_{region}results-{res_speed}-sym.npy",
        allow_pickle=True,
    ).item() # requires an older version of eelbrain!! .39

    # get the fROI and create an annotation
    lh_mask, rh_mask = get_froi_res(
        results, mri_dir=mri_dir, speed=res_speed, mirror=True, save_annot=False, first=False
    )

    lh_mask.color = to_rgba(lh_mask.color)
    rh_mask.color = to_rgba(rh_mask.color)
    res_roi = lh_mask + rh_mask

    lh_mask.save(mri_dir / 'fsaverage_sym'/f'ANOVA_{res_speed}_p0.01_fROI.label')
    rh_mask.save(mri_dir / 'fsaverage_sym'/f'ANOVA_{res_speed}_p0.01_fROI.label')
else:
    lh_mask = mne.read_label(mri_dir / 'fsaverage_sym'/f'ANOVA_{res_speed}_p0.01_fROI-lh.label', subject='fsaverage_sym', color="#b0c885")
    rh_mask = mne.read_label(mri_dir / 'fsaverage_sym'/f'ANOVA_{res_speed}_p0.01_fROI-rh.label', subject='fsaverage_sym', color="#b0c885")

    res_roi = lh_mask + rh_mask



""" ------------------ Analysis ------------------ """

# change path dep on analysis
mod_res = {}
#alpha = 1 # only selecting this as the subject level might be double dipping yikes
pval = 0.05

speeds = args.speed

for speed in speeds:
            out_dir = get_path("glm_results") / speed
            out_dir.mkdir(parents=True, exist_ok=True)

            print(f"\n{'='*50}\nDoing {speed} with pmin = {pval}\n{'='*50}")


            # create the results dictionary
            print(f"Loading in the subjects' results...")
            print(res_dir)
            subj = subjects[0]
            resfname = f"{subj}-allconds_{speed}-regressionresults.npy" # new res fname
            vals = np.load(res_dir / resfname, allow_pickle=True).item()
            reg_labels = vals["reg_labels"]
            
            # Clean the labels
            clean_labels = clean_regressor_labels(reg_labels)
            print(clean_labels)

            mod_res = {label: [] for label in clean_labels}
            subjectslist, grouplist = [], []
            
            # load results dict
            for subj in subjects:
                stc_dict = process_subject(subj,speed, res_dir, mri_dir,fs)
                for reg, stc in stc_dict.items():
                    mod_res[reg].append(stc)
                subjectslist.append(subj)
                grouplist.append(get_subj_group(log_dir, subj))

            for model, results in mod_res.items():
                print(f"Beginning model {model}...")
                ds = e.Dataset()
                ds["subject"] = e.Factor(subjectslist, random=True)  # within subj
                ds["group"] = e.Factor(grouplist, random=False)
                ds["src"] = e.load.fiff.stc_ndvar(
                    results, "fsaverage_sym", "ico-4", mri_dir
                )
                print(f"Full dataset created and morphed for {model}!")
    
                # save the ds for post-hoc plotting
                with open(
                    out_dir/ f"{model}_ds.npy",
                    "wb",
                ) as f:
                    np.save(f, ds)
                # get ROI
                src = ds["src"]
                resroi = src.sub(source=res_roi)

                print("STCs subset to area of interest. Starting one sample t-test!")


                # Actual test
                res = e.testnd.TTestOneSample(
                    resroi,
                    ds=ds,
                    samples=10000,  # number of permutations
                    pmin=pval,  # threshold for clusters (uncorrected p-value)
                    tstart=0,  # start of the time window of interest
                    # tstop=0.65,  # stop of the time window of interest
                    mintime=0.40,  # minimum duration for clusters
                    minsource=20,  # minimum number of sources for clusters
                )

                res.clusters.sort("p")
                table = res.clusters.as_table()
                print(f"Results for {model}:\n", table)
                # try adding a paired t-test between story and sentences
                with open(
                    out_dir
                    / f"{model}_all_cond-{speed}-p{pval}-results.npy",
                    "wb",
                ) as f:
                    np.save(f, res)
                
                table.save_txt(
                    out_dir
                    / f"{model}_allcond-{speed}-p{pval}-results.txt"
                    #/ f"{model}_{cond}-{speed}_thresh{alpha}-p{pval}-results.txt"

                )
                
                plotter = ClusterPlotter(
                    ds, mri_dir, out_dir, match="Subject", mode="regression"
                )
                
                try:           
                    plotter.reg_plotb(
                        res.clusters, 
                        effect=model, 
                        surf="inflated")
                    
                    plotter.reg_plot(
                        res.clusters, 
                        effect=model)
                except:
                    print("oh no")
                    continue
                    
                print('Moving onto next condition...\n')
