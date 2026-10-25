# Structure-Speed

This repo contains all the necessary scripts to run the MEG and behavioral analyses for the paper: Temporal constraints on the neural signatures of narrative processing [(Messi, Bhuyain and Pylkkanen, 2026)](https://elifesciences.org/reviewed-preprints/112198/reviews). 

## Repository layout

- `analysis/`: GLM and ANOVA scripts
- `visualization/`: plotting scripts.
- `preprocessing/`: quality-control, preprocessing, and source-estimation notebooks.
- `stimulus/`: Python and R scripts for preparing story stimuli and task trials.
- `behavioral/`: R scripts for cleaning and analyzing MEG behavioral data.
- `helperfunctions.py`: helper functions used across all scripts and notebooks.
- `project_config.py` and `project_config.json`: shared path configuration for all scripts.
- `structure_speed_requirements.txt`: core Python requirements.

## Data availability
All MEG data is available here: INSERT PATH

## Project set up 

### Path configuration
Paths have been changed in this script to function on other devices. Edit `project_config.json` and set `project_root` to the folder that contains all the necessary project folders. Individual paths can be overwritten in the JSON script or in the individual scripts.

### Python environment
All necessary python packages are included in [`structure_speed_requirements.txt`](./structure_speed_requirements.txt). You can use the requirement file to recreate the conda environment necessary to run the analyses. 

### Script inputs and outputs

| Script | Main inputs | Main outputs |
| --- | --- | --- |
| `preprocessing/preprocessing.ipynb` | Raw MEG data | Preprocessed epochs: `<subject>_IdvDiff_final-epo.fif` |
| `preprocessing/source.ipynb` | Preprocessed epochs, subject source/forward files, and FreeSurfer T1 | Source-localized epochs |
| `analysis/GLM_cond.py` | preprocessed single-trials epochs and source-estimation files | .npy files of beta weights per regressor; saved design matrices in `figures`|
| `analysis/ANOVA-final.py` | Source-localized evoked responses | ANOVA dataset and results |
| `analysis/GLM_stats.py` | Subject GLM result files, ANOVA cluster results, FreeSurfer labels, and subject logs | Speed-specific GLM datasets, cluster statistics, and plots under `glm_results/<speed>/` |
| `visualization/plot.py` | ANOVA dataset, `-sym.npy` cluster results, and `fsaverage_sym` fROI labels | ANOVA figures under `figures` |
| `visualization/fancyplot.py` | GLM dataset and cluster result files under `glm_results/<speed>/` | GLM brain plots under `glm_figures` |
| `stimulus/chunktext.py` → `stimulus/logcreator.py` | Story text, followed by manually reviewed chunk output | Chunk TSV, followed by a final stimulus TSV under `stimuli` |
| `stimulus/word_stimuli.py` | `story<story-number>_final_stim.tsv` | Scrambled CSV and word-count CSV under `stimuli` |
| `stimulus/createtaskstim.py` | Final stimulus TSV files for stories 1–3 | Task stimulus TSV files under `stimulus_task` |
| `behavioral/MEG_taskanalysis.R` | Subject MEG logs, `logs/Subject_task_rts.csv`, and `behavioral/comp.csv` | Behavioral task summaries, statistical analyses, and plots |
| `behavioral/clean_behav.R` | Raw experiment CSVs, task-table CSVs | Cleaned behavioral data under `behavioral/preproc/` |

The project does not bundle these inputs. Check the required files and external
FreeSurfer assets before running the corresponding script. ANOVA cluster files
use the `-sym.npy` suffix consistently; GLM statistics and ANOVA visualization
expect that same suffix.

### Importing scripts

Three scripts are commandline scripts that should be run directly without importing them: `analysis/ANOVA-final.py`,`analysis/GLM_stats.py`, and `visualization/fancyplot.py`. 
The subject-level GLM can be run with:

```sh
python analysis/GLM_cond.py --subj <subject-id> --speed fast
```

The group-level GLM statistics accept one or more speed values:

```sh
python analysis/GLM_stats.py --speed slow fast
```

The GLM results plotter takes a speed and a model name:

```sh
python visualization/fancyplot.py --speed fast --model Intercept
```

Model names supported by the plotter are the same as the regressors from the final paper: `Intercept`, `scrambled`,`scrambled:trl_scaled`, `sents`, `sents:trl_scaled`, and `trl_scaled_centered`.

The GLM and ANOVA workflows are computationally intensive and require the
corresponding configured input data and scientific Python environment.