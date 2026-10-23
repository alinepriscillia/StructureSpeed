# Plot selected GLM source-space clusters for a speed and model.



import os, sys
import numpy as np
from pylab import *
import eelbrain as e
import mne
import argparse
from pathlib import Path
from functools import reduce
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D


PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from project_config import get_path
from helperfunctions import get_MNE_NDVAR, plot_MNE_brain, get_froi_res

# ---------------#
# Paths
# ---------------#
e.configure(frame=False)

PATH = get_path("project_root")
main_dir = get_path("data")
mri_dir = get_path("mri")
stc_dir = get_path("stc")
res_dir = get_path("glm_results")
out_dir = get_path("glm_figures")

os.chdir(main_dir)

parser = argparse.ArgumentParser(description="What analysis do you want to plot?")
parser.add_argument('--speed', type=str)
parser.add_argument('--model', type=str)

args = parser.parse_args()


# ---------------#
# Script
# ---------------#
""" ------------------ Variables ------------------ """
pval = 0.05

# code to isolate the greens only for plotting anova results
cmap = "PiYG"
original_cmap = plt.cm.PiYG
start_point = 0.5
end_point = 1
colors = original_cmap(np.linspace(start_point, end_point, 256))
piyg_green_only = LinearSegmentedColormap.from_list("PiYG_Truncated", colors)

start_point = 0
end_point = 0.5
colors = original_cmap(np.linspace(start_point, end_point, 256))
piyg_pink_only = LinearSegmentedColormap.from_list("PiYG_Pinks", colors)


# Font specs
fm = matplotlib.font_manager
matplotlib.rcParams.update({"font.size": 10})
matplotlib.rcParams["font.family"] = "Arial"

""" ------------------ Get and plot each cluster ------------------ """
out_dir = get_path("glm_figures")
out_dir.mkdir(parents=True, exist_ok=True)


# -------------
# cnum_scaled
#--------------

# Type of script
speed = args.speed
model_name = args.model

ds_dir = res_dir / speed
modelds_path = ds_dir / f"{model_name}_ds.npy"

res_path = (
    ds_dir
         / f"{model_name}_all_cond-{speed}-p{pval}-results.npy"
)
print('Loading in results...')
results = np.load(res_path, allow_pickle=True).item()
ds = np.load(modelds_path, allow_pickle=True).item()

lh_res, rh_res = get_froi_res(results, mri_dir, speed=speed, mirror=False, sig = False)
if lh_res is None and rh_res is None :
    print(f"--- Skipping {model_name}: No results found. ---")
    sys.exit(0)  # Exit with 0 so the Bash script thinks everything is fine and continues
print('Clusters extracted! Beginning plotting loop...')

'''
clim = {
    "kind": "value",
    "pos_lims": [0, 0.18, 0.60],
}  # all cluster breakdowns; pos_lims to have it diverge the way it's supposed to
'''
# fast in comments
model_clims = {'Intercept': {
    "kind": "value",
     #"pos_lims": [0, 11, 33], 
    "pos_lims": [0, 8.3, 25] # fast
}, 'scrambled:trl_scaled': {
    "kind": "value",
    "pos_lims": [0, 0.5, 1.5],
}, 'sents:trl_scaled': {
    "kind": "value",
    "pos_lims": [0, 0.14, 0.4],
}, 
'sents': {
    "kind": "value",
    #"pos_lims": [0, 1.1, 3.3], 
      "pos_lims": [0,0.86,2.6] # fast
}, 
 'scrambled': {
    "kind": "value",
    #"pos_lims": [0, 1.9, 5.7], 
    "pos_lims": [0,1.4,4.2] # fast
}, 
'trl_scaled_centered': {
    "kind": "value",
    "pos_lims": [0, 0.33, 1]}
}
#
clus = []
for clu_id in results.clusters["id"]:
    # get the cluster
    sel_clu = results.clusters[results.clusters["id"] == clu_id][
        0
    ]  # selecting cluster based on the ID
    clu = sel_clu["cluster"]
    clus.append(clu)

stc = get_MNE_NDVAR(
    reduce(lambda x, y: x + y, clus)
)  # add the clusters together and create one stc
cluster_brain = plot_MNE_brain(
    stc.mean(),
    ["lat", "med"],
    mri_dir,
    hemi="split",
    colormap='PiYG',
    annot=False,
    colorbar=False,
    clim=model_clims[model_name],
    title=str(model_name),
)
# cluster_brain.set_data_smoothing(5)
cluster_brain.save_image(filename=out_dir / f"{model_name}-bilat_{speed}.png")
print(f'{model_name}:{max(abs(stc.mean().data))}')
print('Done!!\n')


# plot the colorbar
#fig, ax = plt.subplots()
#cbar = mne.viz.plot_brain_colorbar(
    #ax, clim, "PiYG", orientation="horizontal", label="Beta (t)"
#)
#ax.set_xlim(-1.5, 0)  # crop the axes to only reflect the negative portion
# plt.xticks([], [])
#plt.rcParams["figure.figsize"] = [12, 4]
#plt.savefig(out_dir / f"{model_name}-colobar.pdf", bbox_inches="tight")
# Show the plot
#plt.show()


