# file with helper functions used across analyses
import os
import mne
import re
import tqdm
import numpy as np
from functools import reduce
import operator
# import eelbrain as e
import pandas as pd
from pathlib import Path
from scipy.stats import false_discovery_control

# -----------------------#
# Subject info functions
# -----------------------#


def get_subj_group(log_dir, subj):
    """
    Get a subject's stimulus-order group letter from their logfile name.

    Args:
        log_dir: Directory containing subject-specific log directories.
        subj: Subject identifier used to locate the subject's log directory.

    Returns:
        The group letter encoded in the matching logfile name.
    """

    logfile = [
        f
        for f in os.listdir(os.path.join(log_dir, subj))
        if "logfile" in f and "extra" not in f
    ][0]
    match = re.search(r"group([A-Za-z])", logfile)
    if match:
        group = match.group(1)
        print(group)
    else:
        print("No match found")
    return group


def find_white_rectangle_photodiode(raw, trigger_channel='STI 014', max_delay_ms=150):
    """
    Find photodiode signal for white rectangle within specified delay of triggers.
    
    Parameters:
    -----------
    raw : mne.io.Raw
        Raw MEG data
    trigger_channel : str
        Channel name for triggers (default: 'STI 014')
    max_delay_ms : int
        Maximum delay in milliseconds to search for photodiode response (default: 150)
    
    Returns:
    --------
    tuple : (best_channel, delay_info, response_percentage)
    """
    # Find triggers on the specified channel
    events = mne.find_events(raw, stim_channel=trigger_channel, min_duration=0.002)
    print(f"Found {len(events)} triggers on {trigger_channel}")
    
    # Convert max_delay to samples
    max_delay_samples = int(max_delay_ms * raw.info['sfreq'] / 1000)
    
    # Test all MISC channels
    misc_channels = [f'MISC {i:03d}' for i in range(1, 33)]
    best_channel = None
    best_delay_info = None
    best_percentage = 0
    
    print(f"Searching for photodiode response within {max_delay_ms}ms of triggers...")
    
    for _,channel in tqdm(enumerate(misc_channels), total=len(misc_channels), desc= 'MISC channels'):
        try:
            #print(f"Testing channel: {channel}")
            
            # Get photodiode data
            pd_idx = np.array(raw.info['ch_names']) == channel
            if not np.any(pd_idx):
                print(f"  -> Channel {channel} not found")
                continue
                
            pd_data = raw._data[pd_idx][0]
            
            # Analyze each trigger
            responses = []
            delays = []
            
            for event_time in events[:, 0]:
                # Adjust for sampling differences
                tw = event_time - raw.first_samp
                
                # Look for response within max_delay_samples
                window = pd_data[tw:tw + max_delay_samples]
                
                # Calculate baseline (100 samples before trigger with 50 sample buffer)
                baseline_start = max(0, tw - 150)
                baseline_end = max(0, tw - 50)
                baseline = pd_data[baseline_start:baseline_end]
                
                if len(baseline) > 0:
                    blmean = np.mean(baseline)
                    blsd = np.std(baseline)
                    threshold = blmean + 20 * blsd  # More conservative threshold
                    
                    # Find first crossing above threshold
                    response_indices = np.where(window > threshold)[0]
                    
                    if len(response_indices) > 0:
                        delay = response_indices[0]
                        delays.append(delay)
                        responses.append(event_time + delay)
            
            # Calculate statistics
            if len(delays) > 0:
                mean_delay = np.mean(delays) / raw.info['sfreq'] * 1000  # Convert to ms
                std_delay = np.std(delays) / raw.info['sfreq'] * 1000
                response_percentage = len(delays) / len(events) * 100
                
                #print(f"  -> {response_percentage:.1f}% response rate")
                #print(f"  -> Mean delay: {mean_delay:.1f} ± {std_delay:.1f} ms")
                
                # Update best channel if this one has better response rate
                if response_percentage > best_percentage:
                    best_percentage = response_percentage
                    best_channel = channel
                    best_delay_info = (mean_delay, std_delay, response_percentage)
                    #print(f"  -> New best channel!")
            else:
                print(f"  -> No responses found")
                
        except Exception as e:
            print(f"  -> Error with {channel}: {e}")
    
    return best_channel, best_delay_info, best_percentage


def get_task_onsets(events):
    """Extract task-trigger samples, condition names, and trial numbers."""
    event_id = {
        160: "scrambled_fast",
        161: "scrambled_slow",
        162: "sents_fast",
        163: "sents_slow",
        164: "intact_fast",
        165: "intact_slow",
    }
    task_onsets = []
    condition = None
    trial_num = 1

    for index, (sample, _, trigger) in enumerate(events):
        if trigger in event_id:
            condition = event_id[trigger]
            trial_num = 1
        elif (
            trigger == 166
            and condition is not None
            and index + 1 < len(events)
            and events[index, 1] == 0
        ):
            task_onsets.append([sample, trial_num, condition])
            trial_num += 1

    return task_onsets


def make_subj_df(task_onsets, subj):
    """Build a task-trial table and derive reaction times from sample times."""
    df = pd.DataFrame(task_onsets, columns=["sample", "Trial_num", "Condition"])
    df["rt"] = -df.groupby("Condition")["sample"].diff(-1)
    df["Participant"] = subj
    return df


# -------------#
# ROIs
# -------------#


def get_hemis(mri_dir):
    """Gets the right and left hemispheres without the medial wall"""

    annot_name = "PALS_B12_Lobes"
    lobes = mne.read_labels_from_annot(
        "fsaverage", annot_name, subjects_dir=mri_dir, hemi="lh"
    )
    label_name = "LOBE.FRONTAL-lh"
    lh_frontal = [label for label in lobes if label.name == label_name][0]
    label_name = "LOBE.LIMBIC-lh"
    lh_limbic = [label for label in lobes if label.name == label_name][0]
    label_name = "LOBE.OCCIPITAL-lh"
    lh_occipital = [label for label in lobes if label.name == label_name][0]
    label_name = "LOBE.PARIETAL-lh"
    lh_parietal = [label for label in lobes if label.name == label_name][0]
    label_name = "LOBE.TEMPORAL-lh"
    lh_temporal = [label for label in lobes if label.name == label_name][0]

    LH = lh_frontal + lh_limbic + lh_occipital + lh_parietal + lh_temporal

    lobes = mne.read_labels_from_annot(
        "fsaverage", annot_name, subjects_dir=mri_dir, hemi="rh"
    )
    label_name = "LOBE.FRONTAL-rh"
    rh_frontal = [label for label in lobes if label.name == label_name][0]
    label_name = "LOBE.LIMBIC-rh"
    rh_limbic = [label for label in lobes if label.name == label_name][0]
    label_name = "LOBE.OCCIPITAL-rh"
    rh_occipital = [label for label in lobes if label.name == label_name][0]
    label_name = "LOBE.PARIETAL-rh"
    rh_parietal = [label for label in lobes if label.name == label_name][0]
    label_name = "LOBE.TEMPORAL-rh"
    rh_temporal = [label for label in lobes if label.name == label_name][0]
    label_name = "MEDIAL.WALL-rh"

    RH = rh_frontal + rh_limbic + rh_occipital + rh_parietal + rh_temporal

    WB = LH + RH
    return WB, LH, RH


def get_narrative_ROI(mri_dir, hemi):
    """Build the project’s narrative-related cortical ROIs for one hemisphere."""
    # load in different annotations
    annot_name = "aparc_sub"
    aparcsub = mne.read_labels_from_annot(
        "fsaverage_old", annot_name, subjects_dir=mri_dir, hemi=hemi
    )

    annot_name = "aparc"
    aparc = mne.read_labels_from_annot(
        "fsaverage_old", annot_name, subjects_dir=mri_dir, hemi=hemi
    )

    annot_name = "PALS_B12_Brodmann"
    brodmann = mne.read_labels_from_annot(
        "fsaverage_old", annot_name, subjects_dir=mri_dir, hemi=hemi
    )

    # aparc sub

    # posterior STS
    name_list = [f"bankssts_2-{hemi}", f"bankssts_3-{hemi}"]  # excluding 1
    label_list = [label for label in aparcsub if label.name in name_list]
    sts = reduce(operator.add, label_list)
    # anterior MTG
    name_list = [
        f"middletemporal_4-{hemi}",
        f"middletemporal_5-{hemi}",
        f"middletemporal_6-{hemi}",
    ]  # only 4-6
    label_list = [label for label in aparcsub if label.name in name_list]
    mtg = reduce(operator.add, label_list)

    # aparc

    # Precuneus
    name = f"precuneus-{hemi}"
    pre = [label for label in aparc if label.name == name][0]
    # DMPFC
    name_list = [f"superiorfrontal-{hemi}", f"frontalpole-{hemi}"]
    label_list = [label for label in aparc if label.name in name_list]
    dmpfc = reduce(operator.add, label_list)
    # IFG/ Frontal operculum
    name_list = [f"parstriangularis-{hemi}", f"parsopercularis-{hemi}"]
    label_list = [label for label in aparc if label.name in name_list]
    ifg = reduce(operator.add, label_list)

    # Brodmann

    # AG + SMG
    name_list = [f"Brodmann.40-{hemi}", f"Brodmann.39-{hemi}"]
    label_list = [label for label in brodmann if label.name in name_list]
    ag = reduce(operator.add, label_list)
    # Pre-motor area
    pma = [label for label in brodmann if label.name == f"Brodmann.6-{hemi}"][0]
    mid_z = np.median(pma.pos[:, 2])  # Use median y-coordinate

    # Select only vertices in the lower half
    lower_half_mask = pma.pos[:, 2] < mid_z
    lower_vertices = pma.vertices[lower_half_mask]

    # Create new label for the lower half
    ba6_lower_label = mne.Label(
        vertices=lower_vertices,
        pos=pma.pos[lower_half_mask],
        values=pma.values[lower_half_mask],
        hemi=pma.hemi,
        name=pma.name + "-lower",
        subject=pma.subject,
    )

    return [sts, mtg, pre, dmpfc, ifg, ag, ba6_lower_label]


def get_OFC_aparc(mri_dir, subject="fsaverage"):
    """Get left and right hemisphere labels (without medial wall)
    from the aparc parcellation."""

    annot_name = "aparc"  # use Desikan–Killiany atlas

    # Left hemisphere
    lh_labels = mne.read_labels_from_annot(
        subject, annot_name, subjects_dir=mri_dir, hemi="lh"
    )
    # Remove medial wall / non-cortical labels
    lh_labels = [
        lab
        for lab in lh_labels
        if any(x in lab.name.lower() for x in ["orbitofrontal"])
    ]
    LH = sum(lh_labels[1:], lh_labels[0])  # combine all LH labels into one

    # Right hemisphere
    rh_labels = mne.read_labels_from_annot(
        subject, annot_name, subjects_dir=mri_dir, hemi="rh"
    )
    rh_labels = [
        lab
        for lab in rh_labels
        if any(x in lab.name.lower() for x in ["orbitofrontal"])
    ]
    RH = sum(rh_labels[1:], rh_labels[0])  # combine all RH labels into one

    return LH, RH


# ---------------------#
# Trialwise operations
# ---------------------#


def get_raws(meg_dir):
    """Load and concatenate the subject's primary raw FIF files."""
    raw_dir = os.path.join(meg_dir, "raw")
    files = os.listdir(raw_dir)

    # choose only the main files not the MNE extra ones bc of file size
    unique_files = sorted(
        set(f for f in files if f.endswith(".fif") and "IdvDiff" in f and "-1" not in f)
    )
    if not unique_files:
        raise FileNotFoundError(f"No primary IdvDiff FIF files found in {raw_dir}")

    # Read raw files
    raws = [
        mne.io.read_raw_fif(os.path.join(raw_dir, f), preload=True)
        for f in unique_files
    ]
    print(len(raws))

    if len(raws) == 1:
        raw = raws[0]
    else:
        print("Multiple raw files... Concatenating")
        raw = mne.concatenate_raws(raws, on_mismatch="ignore")
    return raw


def select_condition(trials, condition, crop=False):
    """
    Function that selects the trials for a condition and demeans the data
    """
    data = trials[f"Condition=='{condition}'"]
    if crop:
        if "fast" in condition:
            data = data.crop(0, 0.45)  # keep everything not cropped
    else:
        print("NOT CROPPED")
    # demean across epoch
    print("DEMEANING EPOCHS NOW")
    if "fast" in condition:
        data = data.apply_baseline(
            baseline=(0, 0.45)
        )  # demean only over -100 to 450ms for fast?
    else:
        data = data.apply_baseline(baseline=(None, None))
    return data


# -----------------#
# Source space
# -----------------#

def make_inverse(subj, cleandata, fixed=False, meg_dir=None):
    """
    Build an MNE inverse operator from a subject's forward and covariance files.

    Args:
        subj: Subject identifier used to locate source files.
        cleandata: Cleaned MNE data object supplying the measurement info.
        fixed: Whether to construct a fixed-orientation inverse operator.
        meg_dir: MEG data directory; defaults to the configured project path.

    Returns:
        The MNE inverse operator for the subject.
    """
    if meg_dir is None:
        from project_config import get_path

        meg_dir = get_path("meg")
    source_dir = Path(meg_dir) / subj / "source"
    cov_fname = source_dir / f"{subj}-cov.fif"
    fwd_fname = source_dir / f"{subj}-fwd.fif"

    fwd = mne.read_forward_solution(fwd_fname)
    cov = mne.read_cov(cov_fname)
    print("\n Forward solution and covariance matrix loaded...")

    info = cleandata.info

    inv = mne.minimum_norm.make_inverse_operator(
        info, fwd, cov, depth=0.8, loose="auto", fixed=fixed
    )
    print("\n Inverse solution loaded...")
    return inv

def make_single_trials(subj, cleandata, fixed=False, meg_dir=None):
    """
    Estimate dSPM source activity for each epoch in the cleaned data.

    Args:
        subj: Subject identifier used to locate source files.
        cleandata: Cleaned MNE epochs to inverse-estimate.
        fixed: Whether to use a fixed-orientation inverse operator.
        meg_dir: MEG data directory; defaults to the configured project path.

    Returns:
        A tuple containing the inverse operator and a generator of epoch estimates.
    """
    inv = make_inverse(subj, cleandata, fixed=fixed, meg_dir=meg_dir)
    print("\n Inverse solution loaded...")
    
    SNR = 2
    lambda2 = 1.0 / SNR**2.0

    sing_trstcs = mne.minimum_norm.apply_inverse_epochs(
        cleandata, inv, lambda2, verbose=False, method="dSPM",
        return_generator=True
    )

    return inv, sing_trstcs


def get_source_reqs(subj, info, PATH=None, fixed=False):
    """
    Create or load source-space, BEM, forward, and inverse solutions.

    PATH is the project root. When omitted, use the configured project root.
    """
    if PATH is None:
        from project_config import get_path

        PATH = get_path("project_root")
    PATH = Path(PATH)

    meg_dir = PATH / "data" / "meg"
    mri_dir = PATH / "data" / "mri"

    # Filenames
    trans_fname = meg_dir / subj / f"{subj}-trans.fif"
    bem_fname = mri_dir / subj / "bem" / f"{subj}-inner_skull-bem-sol.fif"
    src_fname = mri_dir / subj / "bem" / f"{subj}-ico-4-src.fif"
    source_dir = meg_dir / subj / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    fwd_fname = source_dir / f"{subj}-fwd.fif"
    cov_fname = source_dir / f"{subj}-cov.fif"

    # Create source space
    if not os.path.isfile(src_fname):
        print("Setting up source space")
        src = mne.setup_source_space(subject=subj, spacing="ico4", subjects_dir=mri_dir)
        src.save(src_fname, overwrite=True)
    else:
        print("src for subj = %s already exists, loading file..." % subj)
        src = mne.read_source_spaces(src_fname)
        print("Source space completed!")

    # Get BEM model
    print("Getting BEM model")
    if not os.path.isfile(bem_fname):
        print("BEM model for subj = %s does not exist, creating file." % subj)
        conductivity = (0.3,)  # for single layer
        model = mne.make_bem_model(
            subject=subj, ico=4, conductivity=conductivity, subjects_dir=mri_dir
        )
        bem = mne.make_bem_solution(model)
        mne.write_bem_solution(bem_fname, bem)
        print("Done. BEM saved.")

    # Get forward solution
    print("Getting forward solution")
    if not os.path.isfile(fwd_fname):
        print("forward solution for subj = %s does not exist, creating file." % subj)
        fwd = mne.make_forward_solution(
            info=info, trans=trans_fname, src=src, bem=bem_fname, ignore_ref=True
        )
        mne.write_forward_solution(fwd_fname, fwd, overwrite=True)
    else:
        print("fwd for subj = %s already exists, loading file..." % subj)
        fwd = mne.read_forward_solution(fwd_fname)
        print("Done.")

    # Get inverse operator
    print("Calculating inverse operator")
    cov = mne.read_cov(cov_fname)
    if fixed:  # for signed data
        fwd = mne.convert_forward_solution(fwd, surf_ori=True)

    inv = mne.minimum_norm.make_inverse_operator(
        info, fwd, cov, depth=0.8, loose="auto", fixed=fixed
    )  # loose sets how offset from perpendicular the dipoles are
    print("Done!")

    return inv


def beamformer_prereqs(
    subj,
    cleandata,
    meg_dir,
    epoch_tmin=0,
    epoch_tmax=0.45,
    reg=0.2,
    pick_ori="normal",
    weight_norm="unit-noise-gain",
):
    """Create LCMV beamformer filters for a subject's cleaned epochs."""
    data_cov = mne.compute_covariance(
        cleandata, tmin=epoch_tmin, tmax=epoch_tmax, method="shrunk"
    )
    print("Covariance computed!")

    source_dir = Path(meg_dir) / subj / "source"
    cov_fname = source_dir / f"{subj}-cov.fif"
    fwd_fname = source_dir / f"{subj}-fwd.fif"
    fwd = mne.read_forward_solution(fwd_fname)
    cov = mne.read_cov(cov_fname)
    print("\nForward solution and covariance matrix loaded...")
    print("Calculating filters for beamforming...")

    from mne.beamformer import make_lcmv

    return make_lcmv(
        cleandata.info,
        fwd,
        data_cov,
        reg=reg,
        noise_cov=cov,
        pick_ori=pick_ori,
        weight_norm=weight_norm,
        inversion="matrix",
        rank=None,
    )


# -----------------#
# Stats
# -----------------#


def get_sig_clu(results, effect=None, pmin=0.05):
    """
    Get significant clusters from ANOVA or regression results.

    Parameters:
    -----------
    results : eelbrain ANOVA.clusters object
        Results containing clusters with "p" column
        For ANOVA: may also have "effect" column
        For regression: no "effect" column
    effect : str, optional
        Filter by specific effect (only used if "effect" column exists in results)
    pmin : float, default=0.05
        P-value threshold for filtering significant clusters

    Returns:
    --------
    sig_clusters : filtered and sorted clusters
    """
    mask_sign_clusters = np.where(results["p"] <= pmin, True, False)
    sig_clusters = results[mask_sign_clusters]

    try:
        # Check if "effect" column exists by trying to access it
        _ = sig_clusters["effect"]
        sig_clusters = sig_clusters[sig_clusters["effect"] == effect]
    except (KeyError, AttributeError):
        pass

    sig_clusters.sort("p")
    return sig_clusters


# -----------------#
# Plotting
# -----------------#


def get_froi_res(
    results, mri_dir, speed="comb", mirror=False, save_annot=False, sig=True, first=False
):
    """Convert selected result clusters into left and right fROI masks."""
    effect = "Structure"
    sig_clusters = get_sig_clu(results.clusters, effect)
    sig_clusters.sort("p")

    if sig:
        if speed == "fast":
            fast_ids = [4, 4798, 4802]
            sig_clusters = sig_clusters[sig_clusters["id"].isin(fast_ids)]
        if speed == "slow":
            slow_ids = [3, 6452, 6456, 11, 9, 6482, 6469]
            sig_clusters = sig_clusters[sig_clusters["id"].isin(slow_ids)]

    lh_labels = []
    rh_labels = []
    lh_mask = None
    rh_mask = None

    # Keep track if we already added a first cluster
    lh_done = False
    rh_done = False

    for i in range(sig_clusters.n_cases):
        cluster = sig_clusters[i]["cluster"]
        e.load.update_subjects_dir(cluster, mri_dir)
        cluster = e.complete_source_space(cluster)
        cluster = e.morph_source_space(
            cluster, "fsaverage_sym", parc="aparc", copy=True
        )
        hemi = sig_clusters[i]["hemi"]
        clus_list = e.labels_from_clusters(cluster)
        label = [label for label in clus_list if "unknown" not in label.name][0]
        label.name = f"Cluster-{i}"
        label.color = tuple(np.append(np.random.rand(3), 1.0))

        if hemi == "lh":
            if not first or not lh_done:
                lh_labels.append(label)
                lh_done = True
            if mirror:
                lh_m, rh_m = e.xhemi(
                    cluster, hemi="rh", parc="aparc"
                )  # mirrored data from lh onto chosen hemi
                sym_list = e.labels_from_clusters(lh_m)
                mirrored = [L for L in sym_list if "unknown" not in L.name][0]
                mirrored.name = f"{label.name}-Rmirror"
                mirrored.color = label.color
                if not first or not rh_done:
                    rh_labels.append(mirrored)
                    rh_done = True

        elif hemi == "rh":
            if not first or not rh_done:
                rh_labels.append(label)
                rh_done = True
            if mirror:
                lh_m, rh_m = e.xhemi(
                    cluster, hemi="lh", parc="aparc"
                )  # mirrored data from the rh onto chosen hemi
                sym_list = e.labels_from_clusters(rh_m)
                mirrored = [L for L in sym_list if "unknown" not in L.name][0]
                mirrored.name = f"{label.name}-Lmirror"
                mirrored.color = label.color
                if not first or not lh_done:
                    lh_labels.append(mirrored)
                    lh_done = True

        # If first=True and both hemispheres have a label, stop loop
        if first and lh_done and rh_done:
            break

    if save_annot:
        if mirror:
            mne.write_labels_to_annot(
                lh_labels,
                overwrite=True,
                subjects_dir=mri_dir,
                subject="fsaverage_sym",
                parc=f"clusters_{effect}({speed})-mir",
                hemi="lh",
            )
            mne.write_labels_to_annot(
                rh_labels,
                overwrite=True,
                subjects_dir=mri_dir,
                subject="fsaverage_sym",
                parc=f"clusters_{effect}({speed})-mir",
                hemi="rh",
            )

        mne.write_labels_to_annot(
            lh_labels,
            overwrite=False,
            subjects_dir=mri_dir,
            subject="fsaverage",
            parc=f"clusters_{effect}({speed})",
            hemi="lh",
        )
        mne.write_labels_to_annot(
            rh_labels,
            overwrite=False,
            subjects_dir=mri_dir,
            subject="fsaverage",
            parc=f"clusters_{effect}({speed})",
            hemi="rh",
        )
    if len(lh_labels)>0:
        lh_mask = reduce(operator.add, lh_labels)
        lh_mask.name = "LH significant mask"
    if len(rh_labels)>0: 
        rh_mask = reduce(operator.add, rh_labels)
        rh_mask.name = "RH significant mask"
    return lh_mask, rh_mask


def plot_MNE_brain(
    stc,
    views,
    mri_dir,
    initial_time=0.1,
    hemi="lh",
    colormap=None,
    annot=True,
    **kwargs,
):
    """Plotting function that takes an stc and makes pretty plots with the settings I like...
    Optional keyword settings include ``clim`` for color limits, ``view_layout``
    for panel arrangement, ``colorbar`` to toggle the color scale, ``size`` for
    figure dimensions, and ``title`` for the plot title. ``annot`` controls
    whether the aparc annotation is added.
    """

    if "title" in kwargs.keys():
        title = kwargs["title"]
    else:
        title = None
    if "clim" in kwargs.keys():  # set the limits if defined
        clim = kwargs["clim"]
    else:
        clim = "auto"  # automatic color limits
    if "size" in kwargs.keys():
        size = kwargs['size']
    else:
        size = 800
    if "view_layout" in kwargs.keys():  # to set horizontal or not
        view_layout = kwargs["view_layout"]
    else:
        view_layout = 'vertical'
    if "colorbar" in kwargs.keys():  # turn the colorbar on or off
        colorbar = kwargs["colorbar"]
    else:
        colorbar = True
    brain = stc.plot(
        "fsaverage_sym",
        subjects_dir=mri_dir,
        initial_time=initial_time,
        surface="smoothwm",
        cortex="low_contrast",
        background="white",
        hemi=hemi,
        views=views,
        colormap=colormap,
        clim=clim,
        view_layout=view_layout,
        colorbar=colorbar,
        size=size,
        title=title,
    )
    if annot:
        brain.add_annotation("aparc", alpha=0.7, color="white")
    return brain


def get_vertices_list(subject, subjects_dir):
    """Load the left- and right-hemisphere source vertices for a subject."""
    # Load the source space for the subject
    src = mne.read_source_spaces(
        f"{subjects_dir}/{subject}/bem/{subject}-ico-4-src.fif"
    )

    # Extract vertices from the source space for left and right hemispheres
    vert_lh = src[0]["vertno"]  # left hemisphere vertex indices
    vert_rh = src[1]["vertno"]  # right hemisphere vertex indices

    return [vert_lh, vert_rh]


def get_MNE_NDVAR(
    cluster,
    complete=False,
    **kwargs,
):
    """
    Function for transforming eelbrain NDVARs into MNE ones
    Takes as input an eelbrain NDVAR/cluster
    """
    if complete:
        cluster = e.complete_source_space(cluster)
    vertices = cluster.get_dim("source").vertices
    subject = cluster.get_dim("source").subject

    time_dim = cluster.get_dim("time")

    if "tmin" in kwargs.keys():  # start time for stc
        tmin = kwargs["tmin"]
    else:
        tmin = time_dim.tmin

    tstep = time_dim.tstep
    data = cluster.get_data(["source", "time"])
    stc = mne.SourceEstimate(
        data, vertices=vertices, tmin=tmin, tstep=tstep, subject=subject
    )

    print(f"STC created successfully with data shape: {stc.data.shape}")

    return stc


# code to workshop to make things streamlined


class ClusterPlotter:
    def __init__(self, ds, mri_dir, out_dir, match="Subject", mode="anova"):
        """
        Unified plotter for ANOVA and Regression clusters.

        ds: eelbrain dataset
        mri_dir: FreeSurfer SUBJECTS_DIR
        out_dir: Path to save plots
        match: variable for matching subjects
        mode: "anova" or "regression"
        """
        self.ds = ds
        self.reset_stc = ds["src"]
        self.mri_dir = mri_dir
        self.out_dir = out_dir
        self.match = match
        if mode not in ["anova", "regression"]:
            raise ValueError("mode must be 'anova' or 'regression'")
        self.mode = mode

    def _get_sig_clusters(self, res, effect=None, pmin=0.05):
        """Select significant clusters based on mode. Uses get_sig_clu for both modes."""
        sig_clusters = get_sig_clu(res, effect, pmin)
        return sig_clusters

    def plot_brain(self, res, effect=None, pmin=0.05, surf="smoothwm", first=False):
        """
        Plot only brain clusters, matching myplotb/reg_plotb functionality.
        First LH/RH if first=True.
        """
        sig_clusters = self._get_sig_clusters(res, effect, pmin)
        if sig_clusters.n_cases is None:
            return

        # Handle effect name for interactions (ANOVA mode)
        if effect and self.mode == "anova":
            effect_display = effect.replace(" x ", "%")
        else:
            effect_display = effect

        lh_done = rh_done = False

        for i in range(sig_clusters.n_cases):
            cluster_nb = i + 1
            cluster = sig_clusters[i]["cluster"]
            tstart = sig_clusters[i]["tstart"]
            tstop = sig_clusters[i]["tstop"]
            location = sig_clusters[i]["location"]
            hemi = sig_clusters[i]["hemi"]

            if hemi == "lh":
                lh_done = True
            if hemi == "rh":
                rh_done = True

            for view in ["lateral", "medial"]:
                brain = e.plot.brain.cluster(
                    cluster.mean(time=(tstart, tstop)),
                    subjects_dir=self.mri_dir,
                    surf=surf,
                    colorbar=False,
                    hemi=hemi,
                    cortex="low_contrast",
                    views=view,
                )
                brain.save_image(
                    self.out_dir
                    / f"Cluster #{cluster_nb}, Effect={effect_display}, cluster at {tstart},{location} - Brain-{view}.png"
                )
                brain.close()

            if first and lh_done and rh_done:
                break

    def plot_timecourse_bars(
        self,
        res,
        effect=None,
        pmin=0.05,
        colors=None,
        labels=None,
        xlim=(0, 0.8),
        ylimits=None,
        bars=None,
        posthoc=None,
        speed=None,
        first=False,
    ):
        """
        Plot timecourse and optionally bars/posthoc, matching myplot/reg_plot functionality.
        Arguments differ by mode:
        - ANOVA: full feature set (colors, labels, bars, posthoc)
        - Regression: bars and posthoc optional, defaults minimal
        """
        sig_clusters = self._get_sig_clusters(res, effect, pmin)
        if sig_clusters.n_cases is None:
            return

        # Handle effect name for interactions (ANOVA mode)
        if effect and self.mode == "anova":
            effect_display = effect.replace(" x ", "%")
        else:
            effect_display = effect

        # Defaults depending on mode
        if self.mode == "regression":
            if bars is None:
                bars = False
            if posthoc is None:
                posthoc = False
            if ylimits is None:
                ylimits = (-0.1, 0)
        else:  # ANOVA
            if bars is None:
                bars = True
            if posthoc is None:
                posthoc = True

        lh_done = rh_done = False
        posthoc_results = []

        for i in range(sig_clusters.n_cases):
            cluster_nb = i + 1
            cluster = sig_clusters[i]["cluster"]
            tstart = sig_clusters[i]["tstart"]
            tstop = sig_clusters[i]["tstop"]
            clu_id = sig_clusters[i]["id"]

            # Get effect from cluster for ANOVA mode (matching myplot behavior)
            if self.mode == "anova":
                cluster_effect = sig_clusters[i]["effect"]
                cluster_effect = cluster_effect.replace(
                    " x ", "%"
                )  # Handle interactions
            else:
                cluster_effect = effect_display

            location = sig_clusters[i]["location"]
            hemi = sig_clusters[i]["hemi"]

            if hemi == "lh":
                lh_done = True
            if hemi == "rh":
                rh_done = True

            # Timecourse
            self.ds["srcm"] = self.reset_stc
            e.load.update_subjects_dir(
                cluster, subjects_dir=self.mri_dir
            )  # updates subjects dir
            clus_list = e.labels_from_clusters(cluster)  # create label
            label = [l for l in clus_list if "unknown" not in l.name][0]
            label.name = f"TempLabel-{hemi}"
            source = self.ds["srcm"].sub(source=label)  # subset dataset to source label
            timecourse = source.mean("source")

            # Create plot - behavior differs by mode
            if self.mode == "anova":
                # ANOVA mode: use cluster_effect in plot
                activation = e.plot.UTSStat(
                    timecourse,
                    cluster_effect,
                    ds=self.ds,
                    title=f"Cluster #{cluster_nb}-{hemi}, [{tstart}-{tstop}]",
                    match=self.match,
                    colors=colors,
                    labels=labels,
                    xlim=xlim,
                    h=6,
                    w=12,
                )
            else:
                # Regression mode: simpler plot without effect variable, only title (matching reg_plot)
                activation = e.plot.UTSStat(
                    timecourse,
                    title=f"Cluster #{cluster_nb}-{hemi}",
                    h=6,
                    w=12,
                    xlim=xlim,
                )

            if ylimits:
                activation.set_ylim(bottom=ylimits[0], top=ylimits[1])
            activation.add_vspan(
                xmin=tstart, xmax=tstop, ymax=0.1, color="lightgrey", zorder=-50
            )
            for fmt in ["png", "pdf"]:
                activation.save(
                    self.out_dir
                    / f"Cluster #{cluster_nb}, ID = {clu_id}, {hemi} - Timecourse.{fmt}"
                )
            activation.close()

            # Optional bar plots (ANOVA mode only, or if explicitly requested)
            if bars and self.mode == "anova":
                self.ds["average_source_activation"] = timecourse.mean(
                    time=(tstart, tstop)
                )
                ymax = self.ds["average_source_activation"].mean()
                bar = e.plot.Barplot(
                    self.ds["average_source_activation"],
                    x=cluster_effect,
                    ds=self.ds,
                    match=self.match,
                    bottom=0,
                    top=ymax + 2,
                    colors=colors,
                    labels=labels,
                    cells=labels.keys() if labels else None,
                    h=6,
                    w=6,
                    # tight=True,
                )
                for fmt in ["png", "pdf"]:
                    bar.save(
                        self.out_dir
                        / f"Cluster #{cluster_nb}, ID = {clu_id}, {hemi} - Bars.{fmt}"
                    )
                bar.close()

            # Optional posthoc (ANOVA only)
            if posthoc and self.mode == "anova":
                conditions = list(labels.keys())
                for j, c1 in enumerate(conditions):
                    for c2 in conditions[j + 1 :]:
                        test_res = e.test.TTestRelated(
                            self.ds["average_source_activation"],
                            x="Structure",
                            ds=self.ds,
                            match=self.match,
                            sub=f"Structure.isin(['{c1}', '{c2}'])",
                        )
                        posthoc_results.append(
                            {
                                "speed": speed,
                                "cluster": cluster_nb,
                                "effect": cluster_effect,
                                "hemi": hemi,
                                "tstart": float(tstart),
                                "tstop": float(tstop),
                                "c1": c1,
                                "c2": c2,
                                "tval": float(test_res.t),
                                "pval": float(test_res.p),
                            }
                        )

            self.ds["src"] = self.reset_stc

            if first and lh_done and rh_done:
                break

        # Save ANOVA posthoc results with significance stars
        if posthoc_results:
            df = pd.DataFrame(posthoc_results)
            df["p_corr"] = false_discovery_control(df["pval"])
            df.to_csv(self.out_dir / "posthoctests.csv")

    # Convenience methods that match original function signatures

    def myplot(
        self,
        res,
        effect,
        pmin=0.05,
        colors=None,
        labels=None,
        xlim=(0, 0.8),
        posthoc=True,
        speed=None,
    ):
        """Convenience method matching myplot() signature for ANOVA mode."""
        if self.mode != "anova":
            raise ValueError("myplot() method requires mode='anova'")
        self.plot_timecourse_bars(
            res,
            effect=effect,
            pmin=pmin,
            colors=colors,
            labels=labels,
            xlim=xlim,
            bars=True,
            posthoc=posthoc,
            speed=speed,
        )

    def myplotb(self, res, effect, pmin=0.05, surf="smoothwm"):
        """Convenience method matching myplotb() signature for ANOVA mode."""
        if self.mode != "anova":
            raise ValueError("myplotb() method requires mode='anova'")
        self.plot_brain(res, effect=effect, pmin=pmin, surf=surf)

    def reg_plot(
        self, res, effect, pmin=0.05, first=False, ylimits=(-0.1, 0), xlim=(0, 0.8)
    ):
        """Convenience method matching reg_plot() signature for regression mode."""
        if self.mode != "regression":
            raise ValueError("reg_plot() method requires mode='regression'")
        self.plot_timecourse_bars(
            res,
            effect=effect,
            pmin=pmin,
            bars=False,
            posthoc=False,
            ylimits=ylimits,
            first=first,
            colors=None,
            xlim=xlim,
        )

    def reg_plotb(self, res, effect, pmin=0.05, surf="smoothwm", first=False):
        """Convenience method matching reg_plotb() signature for regression mode."""
        if self.mode != "regression":
            raise ValueError("reg_plotb() method requires mode='regression'")
        self.plot_brain(res, effect=effect, pmin=pmin, surf=surf, first=first)


# For Regression
# plotter = ClusterPlotter(ds, mri_dir, out_dir, match="Subject", mode="regression")
# plotter.reg_plot(res.clusters, effect="cnum_scaled", ylimits=(-0.15, 0))
# plotter.reg_plotb(res.clusters, effect="cnum_scaled", surf="inflated")
