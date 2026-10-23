# Structure-Speed

This repo contains all the necessary scripts to run the MEG analysis for the paper: Temporal constraints on the neural signatures of narrative processing (Messi, Bhuyain and Pylkkanen, 2026). The files include MEG data preprocesing and quality control, univariate and multivariate analyses as well as plotting and data visualization.

## Repository layout

- `analysis/`: GLM and ANOVA scripts.
- `visualization/`: ANOVA and GLM result-plotting scripts.
- `preprocessing/`: quality-control, preprocessing, and source-estimation notebooks.
- `stimulus/`: Python and R scripts for preparing story stimuli, task sheets, and visual-angle tables.
- `behavioral/`: R scripts for cleaning behavioral data and analyzing MEG task performance.
- `helperfunctions.py`: helpef functions used across scripts and notebooks.
- `project_config.py` and `project_config.json`: shared path configuration.
- `structure_speed_requirements.txt`: core Python environment requirements.

## Data availability

<!-- Fill in the repository/DOI, access conditions, and any restrictions before publication. -->

- Data repository and DOI: [Add repository name, persistent URL, and DOI]
- Data included in this repository: [Specify which data, if any, are included]
- Access to restricted or controlled data: [Describe how eligible researchers can request access]
- Stimuli and other research materials: [Add repository/DOI or explain availability]
- Any data or materials unavailable for sharing: [Identify items and explain restrictions]

## Configure project paths

Edit `project_config.json` and set `project_root` to the data/project root that contains the configured `data/`, `logs/`, and other project folders. Adjust individual entries under `paths` if your directory layout differs. Relative paths are resolved from `project_root`.

For machine-specific configuration without editing the JSON file, set `PROJECT_ROOT`. Individual entries can be overridden with environment variables such as `STRUCTURE_SPEED_PATH_MEG` or `STRUCTURE_SPEED_PATH_GLM_RESULTS`.

## Data and environment

The repository does not include the study data or generated analysis results.
Before running the pipeline, arrange the MEG, MRI/FreeSurfer, source-estimate,
log, behavioral, and stimulus inputs in the configured locations in
`project_config.json`. The source-space analyses also require the
`fsaverage_sym` FreeSurfer subject and the relevant annotations and labels.

Create the core Python environment from
[`structure_speed_requirements.txt`](./structure_speed_requirements.txt):

```sh
conda create --name structure-speed --file structure_speed_requirements.txt
conda activate structure-speed
```

Stimulus generation uses Stanza, which requires its English language model;
visual-angle generation requires the configured background image and a locally
available Futura font. Pillow is constrained to a version below 10 because
`vis_angle.py` uses the legacy `ImageFont.getsize` method. The requirements
file covers Python packages only.

The R workflows require R and packages used by the scripts, including
`jsonlite`, `tidyverse`, `VWPre`, `ggpubr`, `multcomp`, `effectsize`,
`RColorBrewer`, `formattable`, `report`, `lme4`, `car`, `emmeans`, `afex`, and
`cowplot`. Install these separately in R. The repository does not currently pin
R package versions, so results may differ across R environments.

## Additional path configuration

The JSON configuration also defines `stimuli`, `stimulus_task`, `visual_angle`,
`behavioral`, `behavioral_raw`, `word_vectors`, `glm_figures`,
`anova_results`, and `glm_results`. These paths are resolved relative to
`project_root` unless set to absolute paths. The R scripts read the same
`project_config.json` through `project_config.R`; R also honors
`PROJECT_ROOT` and `STRUCTURE_SPEED_PATH_<NAME>` environment overrides.

Keep raw MEG/MRI data, behavioral inputs, stimulus tables, logs, and generated
results in the configured locations. Update the matching `paths` entries before
running scripts when your local folder layout differs.

## Running stimulus scripts

Install the Python dependencies used by the relevant script, including pandas
and Stanza where required. Stanza scripts also need the English model available
in the environment:

```sh
python -c "import stanza; stanza.download('en')"
```

Run `chunktext.py` and `logcreator.py` with optional `--input` and `--output`
paths; their defaults read and write story files under the configured
`stimuli` directory. Run `word_stimuli.py` and enter the story number when
prompted. Run `createtaskstim.py` to create task sheets under
`stimulus_task`, and `vis_angle.py` to calculate visual angles using the
configured stimulus and visual-angle directories. These scripts expect their
input story files, background image, and font assets to be present.

The R stimulus scripts use the configured `stimuli`, `visual_angle`, and
`logs` directories. `clean_behav.R` reads raw experiment files from
`behavioral_raw`, task tables from `stimulus_task`, and writes processed files
under `behavioral`. `MEG_taskanalysis.R` reads MEG subject folders and log
files and expects the configured behavioral comprehension and RT input files.

## Running GLM and ANOVA outputs

`GLM_cond.py` writes subject regression results to `glm_results` and design
figures to `glm_figures`. `GLM_stats.py` reads those regression results and
creates its speed-specific result folders under `glm_results`. The ANOVA
script creates the configured ANOVA results folder and its region/speed
subfolders before writing output. Set the paths in `project_config.json` or
use the documented environment overrides to select writable output locations.

## Script inputs and outputs

| Script | Main inputs | Main outputs |
| --- | --- | --- |
| `preprocessing/preprocessing.ipynb` | Subject MEG recordings and preprocessing settings | Per-subject preprocessed epochs, including `<subject>_IdvDiff_final-epo.fif` |
| `preprocessing/source.ipynb` | Preprocessed epochs, subject source/forward files, and FreeSurfer data | Source estimates under the configured `stc` directory |
| `analysis/GLM_cond.py` | `meg/<subject>/preproc/<subject>_IdvDiff_final-epo.fif` and subject source-space files | `glm_results/<subject>-allconds_<speed>-regressionresults.npy`; design figures under `glm_figures` |
| `analysis/ANOVA-final.py` | Source estimates under `stc/<condition>/` and subject log files | ANOVA dataset and `anova_results/whole/<speed>/Structure_wholeresults-<speed>-sym.npy` plus cluster tables |
| `analysis/GLM_stats.py` | Subject GLM result files, ANOVA cluster results, FreeSurfer labels, and subject logs | Speed-specific GLM datasets, cluster statistics, and plots under `glm_results/<speed>/` |
| `visualization/plot.py` | ANOVA dataset, `-sym.npy` cluster results, and `fsaverage_sym` fROI labels | ANOVA figures under `figures` |
| `visualization/fancyplot.py` | GLM dataset and cluster result files under `glm_results/<speed>/` | GLM brain plots under `glm_figures` |
| `stimulus/chunktext.py` → `stimulus/logcreator.py` | Story text, followed by manually reviewed chunk output | Chunk TSV, followed by a final stimulus TSV under `stimuli` |
| `stimulus/word_stimuli.py` | `story<story-number>_final_stim.tsv` | Scrambled CSV and word-count CSV under `stimuli` |
| `stimulus/createtaskstim.py` | Final stimulus TSV files for stories 1–3 | Task stimulus TSV files under `stimulus_task` |
| `behavioral/MEG_taskanalysis.R` | Subject MEG logs, `logs/Subject_task_rts.csv`, and `behavioral/comp.csv` | Behavioral task summaries, statistical analyses, and plots |
| `behavioral/clean_behav.R` | Raw experiment CSVs, task-table CSVs, and the configured word-vector file | Cleaned behavioral data under `behavioral/preproc/` |

The project does not bundle these inputs. Check the required files and external
FreeSurfer assets before running the corresponding script. ANOVA cluster files
use the `-sym.npy` suffix consistently; GLM statistics and ANOVA visualization
expect that same suffix.

## Importing scripts

Most Python workflow scripts use a `main()` guard and do not start their
workflow when imported. However, `analysis/ANOVA-final.py`,
`analysis/GLM_stats.py`, and `visualization/fancyplot.py` currently execute
their analysis, parse command-line arguments, or load data at module level;
run those as scripts rather than importing them. The subject-level GLM can be
run with:

```sh
python analysis/GLM_cond.py --subj <subject-id> --speed fast
```

The group-level GLM statistics accept one or more speed values:

```sh
python analysis/GLM_stats.py --speed slow fast
```

The GLM cluster plotter takes a speed and a model name:

```sh
python visualization/fancyplot.py --speed fast --model Intercept
```

Model names supported by the plotter are `Intercept`, `scrambled`,
`scrambled:trl_scaled`, `sents`, `sents:trl_scaled`, and
`trl_scaled_centered`.

The GLM and ANOVA workflows are computationally intensive and require the
corresponding configured input data and scientific Python environment.