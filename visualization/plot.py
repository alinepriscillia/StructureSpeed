# Plot ANOVA source-space clusters and fROI results.

import os, sys
import numpy as np
from pylab import *
import eelbrain as e
import mne
from pathlib import Path
from matplotlib.colors import to_rgba
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap


PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from project_config import get_path
from helperfunctions import get_MNE_NDVAR, plot_MNE_brain, get_froi_res

# ---------------#
# Paths
# ---------------#
def main():
    """Plot ANOVA source-space clusters and fROI results."""
    PATH = get_path("project_root")
    main_dir = get_path("data")
    mri_dir = get_path("mri")
    stc_dir = get_path("stc")

    region = "whole"
    res_dir = get_path("anova_results") / region
    ds_dir = get_path("anova_results")
    out_dir = get_path("figures")

    os.chdir(main_dir)

    # ---------------#
    # Script
    # ---------------#
    """ ------------------ Variables ------------------ """
    ds = np.load(ds_dir / "ANOVA_ds-sym.pickle", allow_pickle=True)

    ds["src"] = ds["stcs"]
    ds["srcm"] = ds["src"]

    # create analysis objects
    contrast = "Structure"
    speeds = ["slow", "fast"]
    mapping = {"scrambled": "WordList", "sents": "SentList", "intact": "Story"}
    label_dict = {"Structure": mapping, "Speed": {"fast": "Fast", "slow": "Slow"}}

    # colors!!
    colors = {"scrambled": "#efdda9", "sents": "#cbcf7e", "intact": "#b0c885"}
    colors2 = {"fast": "#daa6ba", "slow": "#74678E"}

    # code to isolate the greens only for plotting anova results
    original_cmap = plt.cm.PiYG
    start_point = 0.5
    end_point = 1.0
    colors_piyg = original_cmap(np.linspace(start_point, end_point, 256))
    piyg_green_only = LinearSegmentedColormap.from_list("PiYG_Truncated", colors_piyg)

    # Font specs
    fm = matplotlib.font_manager
    fm._get_fontconfig_fonts.cache_clear()
    matplotlib.rcParams.update({"font.size": 10})
    matplotlib.rcParams["font.family"] = "Arial"

    """ ------------------ Get and plot fROI ------------------ """

    # get fROI map
    res_speed = "slow"
    lh_mask = mne.read_label(
        mri_dir / "fsaverage_sym" / f"ANOVA_{res_speed}_p0.01_fROI-lh.label",
        subject="fsaverage_sym"
    )
    rh_mask = mne.read_label(
        mri_dir / "fsaverage_sym" / f"ANOVA_{res_speed}_p0.01_fROI-rh.label",
        subject="fsaverage_sym"
    )
    res_roi = lh_mask + rh_mask

    lh_mask.color = colors2[res_speed]
    rh_mask.color = colors2[res_speed]

    # check that shit
    brain = mne.viz.Brain(
        "fsaverage_sym",
        hemi="split",
        surf="smoothwm",
        subjects_dir=mri_dir,
        cortex="low_contrast",
        background="white",
        view_layout="horizontal",
        views=["lat", "med"],
    )
    brain.add_label(lh_mask)
    brain.add_label(rh_mask)
    brain.save_image(filename=out_dir / f"{res_speed}-notmirroredfroi(smooth).png")


    # now do this for fast
    res_speed = "fast"

    res_path = res_dir / res_speed / f"{contrast}_{region}results-{res_speed}-sym.npy"
    results = np.load(res_path, allow_pickle=True).item()
    fast_lh, fast_rh = get_froi_res(
        results, mri_dir, speed=res_speed, mirror=False, first=False
    )

    fast_lh.color = colors2[res_speed]
    fast_rh.color = colors2[res_speed]


    brain = mne.viz.Brain(
        "fsaverage_sym",
        hemi="split",
        view_layout="horizontal",
        views=["lat", "med"],
        surf="smoothwm",
        subjects_dir=mri_dir,
        cortex="low_contrast",
        background="white",
    )
    brain.add_label(fast_lh)
    brain.add_label(fast_rh)

    brain.save_image(filename=out_dir / f"{res_speed}-notmirroredfroi(smooth).png")


    """ ------------------ Get and plot each cluster ------------------ """

    # Type of script
    speed = "slow"
    slow_ids = [3, 6452, 6456, 11, 9, 6482, 6469]

    res_path = res_dir / speed / f"{contrast}_{region}results-{speed}-sym.npy"
    print("symmetrical data")

    slow_results = np.load(res_path, allow_pickle=True).item()
    ds2 = ds.sub("Speed == %r" % speed)

    # replot a more uniform activation timecourse across hemis
    new_clu = slow_results.clusters[
        slow_results.clusters["id"].isin(slow_ids)
    ]

    for clu_id in slow_ids:
        # get the right cluster
        sel_clu = slow_results.clusters[slow_results.clusters["id"] == clu_id][
            0
        ]  # selecting cluster based on the ID
        hemi = sel_clu['hemi']
        tstart = sel_clu["tstart"]
        tstop = sel_clu["tstop"]
    
        cluster = sel_clu['cluster']
        e.load.update_subjects_dir(
                    cluster, subjects_dir=mri_dir
                ) 
        clus_list = e.labels_from_clusters(cluster)  # create label
        label = [l for l in clus_list if "unknown" not in l.name][0]
        label.name = f"TempLabel-{hemi}"
        source = ds2["src"].sub(source=label)  # subset dataset to source label
        timecourse = source.mean("source")
    
        if clu_id in [9,11]:
            max_val = 9
            min_val = 1.5
        elif clu_id in [6482, 6452]:
            max_val = 5
            min_val = 1
        else:
            max_val = 7
            min_val = 1.5

        activation = e.plot.UTSStat(
            timecourse,
            "Structure",
            ds=ds2,
            legend=False,
            title=f"{speed}-{hemi}: Cluster {clu_id}",
            match="Subject",
            colors=colors,
            labels=label_dict["Structure"],
            xlim=(0, 0.8),
            bottom=min_val,
            top=max_val,
            h=2.5,
            w=4,
        )
        activation.add_vspan(
                    xmin=tstart, xmax=tstop, ymax=0.1, color="lightgrey", zorder=-50
                )
        activation.save(out_dir / f"slow-clusterid{clu_id}-{hemi}_timecourse.pdf")
        activation.close()
    
        clu_mean = timecourse.mean(time=(tstart, tstop))
        ymax = clu_mean.mean()
        bar = e.plot.Barplot(
            clu_mean,
            ds = ds2,
            x = 'Structure',
            match="Subject",
            colors=colors,
            xticks = False,
            bottom=0,
            top=ymax + 2,
            cells=label_dict["Structure"].keys(),
            xlabel = False,
            ylabel = False,
            h=3,
            w=3,
            pos = [0.5,1,1.5],
            corr=False
        )
        bar.save(out_dir / f"slow-clusterid{clu_id}-{hemi}_bars.pdf")
        bar.close()



    # do the same for lh
    new_clu = slow_results.clusters[
        slow_results.clusters["id"].isin(slow_ids) & (slow_results.clusters["hemi"] == "lh")
    ]
    # plot the mean activation across clusters
    plot_data = ds2["src"].sub(source=lh_mask)
    timecourse = plot_data.mean("source")

    activation = e.plot.UTSStat(
        timecourse,
        "Structure",
        ds=ds2,
        title=f"{speed} avg timecourse lh",
        match="Subject",
        colors=colors,
        labels=label_dict["Structure"],
        xlim=(0, 0.8),
        bottom=1.5,
        top=5,
    )
    activation.set_clusters(new_clu, color=".8")
    activation.save(out_dir / f"{speed}all_lhclusters - Timecourse.pdf")
    activation.close()


    ## Plot each brain cluster using MNE
    clim = {"kind": "value", "lims": [0, 0.20, 0.5]}  # all cluster breakdowns

    for clu_id in slow_ids:
        # get the rh cluster
        sel_clu = slow_results.clusters[slow_results.clusters["id"] == clu_id][
            0
        ]  # selecting cluster based on the ID
        clu = sel_clu["cluster"]
        stc = get_MNE_NDVAR(clu)
        hemi = sel_clu['hemi']

        cluster_brain = plot_MNE_brain(
            stc.mean(),
            ["lat", "med"],
            mri_dir,
            hemi=hemi,
            colormap=piyg_green_only,
            annot=False,
            colorbar=False,
            clim=clim,
            title=str(clu_id),
            size = (200,400)
        )

        cluster_brain.save_image(filename=out_dir / f"slow-clusterid{clu_id}-{hemi}.png")



    # plot the colorbar
    fig, ax = plt.subplots()
    cbar = mne.viz.plot_brain_colorbar(ax, clim, piyg_green_only, orientation="horizontal", label="Activation (F)")
    #plt.xticks([], [])
    plt.rcParams["figure.figsize"] = [8, 4]
    plt.savefig(out_dir / 'ANOVA-colorbar_both.pdf', bbox_inches='tight')
    # Show the plot
    plt.show()


    ## Doing the same for fast
    speed = "fast"
    fast_ids = [4, 4798, 4802]
    res_path = res_dir / speed / f"{contrast}_{region}results-{speed}-sym.npy"
    results = np.load(res_path, allow_pickle=True).item()

    ds1 = ds.sub("Speed == %r" % speed)

    for clu_id in fast_ids:
        # get the right cluster
        sel_clu = results.clusters[results.clusters["id"] == clu_id][
            0
        ]  # selecting cluster based on the ID
        hemi = sel_clu['hemi']
        tstart = sel_clu["tstart"]
        tstop = sel_clu["tstop"]
    
        cluster = sel_clu['cluster']
        e.load.update_subjects_dir(
                    cluster, subjects_dir=mri_dir
                ) 
        clus_list = e.labels_from_clusters(cluster)  # create label
        label = [l for l in clus_list if "unknown" not in l.name][0]
        label.name = f"TempLabel-{hemi}"
        source = ds1["src"].sub(source=label, time=(0, 0.45))  # subset dataset to source label
        timecourse = source.mean("source")
    
        activation = e.plot.UTSStat(
            timecourse,
            "Structure",
            ds=ds1,
            legend=False,
            title=f"{speed}-{hemi}: Cluster {clu_id}",
            match="Subject",
            colors=colors,
            labels=label_dict["Structure"],
            xlim=(0, 0.8),
            bottom=1,
            top=5,
            h=2.5,
            w=4,
        )
        activation.add_vspan(
                    xmin=tstart, xmax=tstop, ymax=0.1, color="lightgrey", zorder=-50
                )
        activation.save(out_dir / f"fast-clusterid{clu_id}-{hemi}_timecourse.pdf")
        activation.close()
    

        clu_mean = timecourse.mean(time=(tstart, tstop))
        ymax = clu_mean.mean()
        bar = e.plot.Barplot(
            clu_mean,
            ds = ds1,
            x = 'Structure',
            match="Subject",
            colors=colors,
            xticks = False,
            bottom=0,
            top=ymax + 2,
            cells=label_dict["Structure"].keys(),
            xlabel = False,
            ylabel = False,
            h=3,
            w=3,
            pos = [0.5,1,1.5],
            corr=False
        )
        bar.save(out_dir / f"fast-clusterid{clu_id}-{hemi}_bars.pdf")
        bar.close()



    # do the same for lh
    new_clu = results.clusters[
        results.clusters["id"].isin(fast_ids) & (results.clusters["hemi"] == "lh")
    ]
    # plot the mean activation across clusters
    plot_data = ds1["src"].sub(source=fast_lh, time=(0, 0.45))
    timecourse = plot_data.mean("source")

    activation = e.plot.UTSStat(
        timecourse,
        "Structure",
        ds=ds1,
        title=f"{speed} avg timecourse lh",
        match="Subject",
        colors=colors,
        labels=label_dict["Structure"],
        xlim=(0, 0.8),
        bottom=1.5,
        top=5,
    )
    activation.set_clusters(new_clu, color=".8")
    activation.save(out_dir / f"{speed}_all_lhclusters - Timecourse.pdf")
    activation.close()


    fast_clim = {"kind": "value", "lims": [0, 0.20, 0.5]}  # all cluster breakdowns

    for clu_id in fast_ids:
        # get the cluster
        sel_clu = results.clusters[results.clusters["id"] == clu_id][
            0
        ]  # selecting cluster based on the ID
        clu = sel_clu["cluster"]
        hemi = sel_clu["hemi"]
        stc = get_MNE_NDVAR(clu)

        cluster_brain = plot_MNE_brain(
            stc.mean(),
            ["lat", "med"],
            mri_dir,
            hemi=hemi,
            colormap=piyg_green_only,
            annot=False,
            colorbar=False,
            clim=fast_clim,
            title=str(clu_id),
            size = (200,400)
        )

        cluster_brain.save_image(filename=out_dir / f"{speed}-clusterid{clu_id}-{hemi}.png")


if __name__ == "__main__":
    main()
