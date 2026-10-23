#This script runs through all subjects and saves dictionaries with the regression results
# categorical regression with condition x centered trial progression interaction
import mne
import pandas as pd
import numpy as np
import matplotlib # necessary for mne to load in
import statsmodels.api as sm
import patsy
import sys
import argparse
from pathlib import Path
from joblib import Parallel, delayed

import matplotlib.pyplot as plt

# ---------------#
# Paths
# ---------------#

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from project_config import get_path
from helperfunctions import make_single_trials

# ---------------#
# Helper functions
# ---------------#

def create_GLM_design(trials, design, speed, fig_dir, save_plot=False):
    """
    Function that takes the design, makes the full interaction matrix but saves a simplified plot with only main effects
    """
    print("Creating design matrix...")
    # get the log file
    log = trials.metadata.copy().reset_index()
    subj = log["Participant"].unique()[0]
    # create regressors
    log["condition"] = (
        log["Condition"].str.replace(r"_(fast|slow)$", "", regex=True).astype("category")
    )
    log["trl_within_block"] = log.groupby("Condition")["Trial_num"].transform(lambda x: x - x.min())
    log["trl_scaled"] = log["trl_within_block"] / log.groupby("Condition")["cnum"].transform("max")
    log["trl_scaled_centered"] = log["trl_scaled"] - log.groupby("Condition")["trl_scaled"].transform("mean")

    design_matrix = patsy.dmatrix(design, data=log, return_type="dataframe")

    if save_plot:
        simple_formula = design.replace("*", " + ")
        # create a simple main effects design matrix
        simple_design = patsy.dmatrix(simple_formula, data=log, return_type="dataframe")
        reg_labels = simple_design.columns.tolist()
        X_array = (
            simple_design.values if hasattr(simple_design, "values") else simple_design
        )

        # visualize the design matrix
        plt.figure(figsize=(6, 6))
        plt.imshow(X_array, cmap="Blues", interpolation="nearest", aspect="auto")
        plt.xlabel("regressors", fontsize=20)
        plt.ylabel("trial number", fontsize=20)
        plt.xticks(
            ticks=np.arange(0, len(reg_labels)) - 0.2,
            labels=reg_labels,
            rotation=0,
            ha="left",
        )
        plt.tick_params(axis="both", length=0, pad=8, labelsize=10)
        plt.title(subj)
        plt.savefig(fig_dir / f"{subj}_allconds-{speed}_GLMdesign.png")
    print("Design matrix done!")
    return design_matrix, log

def analyze_source(v, n_times, data_mtx, design_matrix):
    """Function to process a single vertex across all time points"""
    # Initialize local arrays for this specific vertex
    n_regs = design_matrix.shape[1]
    b_v = np.empty((n_times, n_regs))
    p_v = np.empty((n_times, n_regs))
    r_v = np.empty((n_times, n_regs))
    r2_v = np.empty(n_times)

    for t in range(n_times):
        y = data_mtx[v, t, :]
        est = sm.OLS(y, design_matrix).fit()

        r2_v[t] = est.rsquared
        b_v[t, :] = est.params
        p_v[t, :] = est.pvalues

        t_vals = est.tvalues
        df = est.df_resid
        r_v[t, :] = np.sign(t_vals) * np.sqrt(t_vals**2 / (t_vals**2 + df))

    return b_v, p_v, r_v, r2_v


# ---------------#
# Script
# ---------------#
def run_subject(
    subj,
    speed,
    meg_dir,
    res_dir,
    fig_dir,
    plot=True,
    n_jobs=-1,
    design="C(condition) * trl_scaled_centered",
    n_sources=5124,
    fixed=False,
):
    """Run the subject-level GLM"""
    np.random.seed(42)
    epoch_tmin = 0
    epoch_tmax = 0.45 if speed == "fast" else 0.8

    print(f"\n{'='*50}\nProcessing: {subj}-{speed} \n{'='*50}")
    epochs_path = meg_dir / subj / "preproc" / f"{subj}_IdvDiff_final-epo.fif"
    cleandata = mne.read_epochs(epochs_path, preload=True)
    cleandata = cleandata.resample(sfreq=500)

    print("Data read in...")
    trials = cleandata["Type=='Trial'"]
    speed_mask = trials.metadata["Condition"].str.endswith(f"_{speed}")
    trials = trials[speed_mask.values]
    trials.crop(epoch_tmin, epoch_tmax)
    trials.apply_baseline(baseline=(None, None))

    print(f"\n{'-' * 20} Continuing with analysis {'-' * 20}")
    design_matrix, _ = create_GLM_design(
        trials, design, speed=speed, fig_dir=fig_dir, save_plot=plot
    )
    reg_labels = design_matrix.columns.tolist()

    _, single_trial_stcs = make_single_trials(
        subj, trials, fixed=fixed, meg_dir=meg_dir
    )
    data_mtx = np.array([stc.data for stc in single_trial_stcs]).transpose(
        1, 2, 0
    )
    n_times = data_mtx.shape[1]
    print(data_mtx.shape)

    del trials
    print(f"\n{'-' * 20} Fitting the regression model {'-' * 20}")
    results = Parallel(n_jobs=n_jobs)(
        delayed(analyze_source)(v, n_times, data_mtx, design_matrix)
        for v in range(n_sources)
    )
    b_map = np.array([result[0] for result in results])
    p_map = np.array([result[1] for result in results])
    r_map = np.array([result[2] for result in results])
    r2_map = np.array([result[3] for result in results])

    result = {
        "beta": b_map,
        "pval": p_map,
        "reg_labels": reg_labels,
        "r_map": r_map,
        "r2_map": r2_map,
    }
    result_path = res_dir / f"{subj}-allconds_{speed}-regressionresults.npy"
    np.save(result_path, result)
    print(f"\n {subj} is saved! \n")
    return result_path


def main(argv=None):
    """Parse command-line options and run the subject-level GLM."""
    parser = argparse.ArgumentParser(
        description="Run GLM for a specific subject and speed"
    )
    parser.add_argument("--subj", type=str, required=True)
    parser.add_argument("--speed", type=str, required=True, choices=["fast", "slow"])
    args = parser.parse_args(argv)

    mne.set_log_level(verbose=30)
    pd.options.mode.chained_assignment = None
    print("Running centered analysis....\n")

    meg_dir = get_path("meg")
    res_dir = get_path("glm_results")
    fig_dir = get_path("glm_figures")
    res_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    return run_subject(
        args.subj,
        args.speed,
        meg_dir=meg_dir,
        res_dir=res_dir,
        fig_dir=fig_dir,
    )


if __name__ == "__main__":
    main()
