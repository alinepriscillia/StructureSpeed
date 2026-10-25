project_dir <- normalizePath(file.path(dirname(script_file), ".."), mustWork = TRUE)
  source(file.path(project_dir, "project_config.R"))

  log_dir <- get_project_path("logs")
  meg_dir <- get_project_path("meg")
  behavioral_dir <- get_project_path("behavioral")
  setwd(log_dir)
  library(ggpubr)
  library(dplyr)
  #library(tidyr)
  #library(psych)
  library(tidyverse)
  library(stringr)
  library(cowplot)
  
  # stats libraries
  library(report)
  library(lme4)
  library(car) # required for the assumption testing for the linear models
  library(emmeans)
  library(multcomp)
  library(afex)  #for p-values with the models
  
  options(scipen=999)

#---------- Helper Functions ----------
get_subj_group <- function(log_dir, subj) {
  # Construct the subject directory path
  subj_dir <- file.path(log_dir, subj)
  
  # List logfiles in the subject directory excluding those with "extra" in the name
  logfiles <- list.files(subj_dir, pattern = "logfile", full.names = FALSE)
  logfiles <- logfiles[!grepl("extra", logfiles)]
  
  if (length(logfiles) == 0) {
    message("No logfile found")
    return(NA)
  }
  
  logfile <- logfiles[1]  # take the first matching logfile
  
  # Use regex to extract the group letter
  match <- regexpr("group([A-Za-z])", logfile, perl = TRUE)
  
  if (match[1] != -1) {
    group <- regmatches(logfile, match)
    # Extract only the group letter (the captured group)
    group_letter <- sub("group", "", group)
    return(group_letter)
  } else {
    message("No match found")
    return(NA)
  }
}

# ----------------- Task accuracy -----------------
# get list of subjects from the meg folder
subjects <- list.dirs(path = meg_dir,
                      recursive = FALSE, full.names = FALSE) %>% keep(~ !grepl("pilot|excluded|notcoreg", .x))
Pattern <- paste(subjects, collapse = "|") 

# get log files for task stats
logs <- list.dirs(recursive = FALSE, full.names = TRUE) %>% # Collapse the vector into a regex pattern
keep(~ grepl(Pattern, .x)) %>%
  # For each subject folder, list logfile*.csv files (non-recursive)
  map(~ list.files(.x, pattern = "logfile.*\\.csv$", full.names = TRUE, recursive = FALSE) |>
        keep(~ !grepl("extra\\.csv$", .))) %>%
  flatten_chr() %>%
  map_dfr(~ read_csv(.x, quote = '"')) 

logs$duplicate[is.na(logs$duplicate)] <- FALSE # remove the duplicates

print(paste("You have", length(subjects), "MEG subjects!"))

final_par <- unique(logs$Participant)


# Isolate the task responses and calculate the relevant rates
task_resp <- logs %>% filter(duplicate== FALSE) %>% filter(Type =='Task') # 30*6*n
if(nrow(task_resp)!= 30*6*length(subjects)){print("Something is off; there's an extra subject")}

# create accuracy column
task_resp <- task_resp %>% mutate(accuracy = ifelse(Task_response ==Correct_answer, 1, 0))

# ------- Reaction Time -------      
# get the reaction time 

rt_raw <- read_csv(file.path(log_dir, "Subject_task_rts.csv")) %>% dplyr::select(-c("...1", "sample"))
print(length(unique(rt_raw$Participant))) # make sure that this is equal to the number of participants!!

task_resp_joined <- task_resp %>% mutate(rt_MEG = rt *1000, Trial_num = Trial_num+1) %>% dplyr::select(-rt) %>%
  left_join(rt_raw, by = c("Participant", "Trial_num", "Condition")) 

# identify the mean delay for people who have both rt methods
delay <- mean(task_resp_joined$rt_MEG - task_resp_joined$rt, na.rm = TRUE) 

task_raw <- task_resp_joined %>% mutate(rt_final = case_when(is.na(rt_MEG)==TRUE ~ rt + delay,
                                                                     .default = rt_MEG)) %>% dplyr::select(Condition, Speed, Participant,accuracy,Judgment, rt_final, Trial_num)
# filter based on hard cutoff and then filter based on participant SD
task_raw <- task_raw %>% mutate(rt = case_when(
    rt_final < 200 ~ NA, # Replace extreme values with NA
    rt_final > 8000 ~ NA,
    TRUE ~ rt_final
  )) %>%
  # remove all trials that are 3sd away from participant mean
  group_by(Participant) %>%
  mutate(
    rt_sd_cutoff = ifelse(abs(scale(rt)) > 3, NA, rt)) %>%
  ungroup() %>% mutate(
    log_rt = log(rt_sd_cutoff)
  ) %>%
  rename(rt_cleaned = rt_sd_cutoff) %>%
  dplyr::select(-rt)

# visualize things
hist(task_raw$rt_cleaned)
report(task_raw) 

# add factors for analysis
task_raw <- task_raw %>% mutate(Structure = case_when(str_detect(Condition, "intact") ~ "Story",
                                          str_detect(Condition, "scrambled") ~ "WordList",
                                          str_detect(Condition, "sents") ~ "SentList")) %>% 
  mutate(Structure = factor(Structure, levels = c('WordList', 'SentList','Story'), ordered=TRUE), 
         group = map_chr(.x = Participant,.f = ~ get_subj_group(log_dir, .x)), 
         Speed = factor(Speed,levels = c('Slow', 'Fast')))


# get rates and accuracies
Rates_all <- task_raw %>% group_by(Condition,Speed,Participant, Structure) %>% summarize(FA = sum(Judgment=='FA')/n(), H = sum(Judgment=='H')/n(),
                                                                                         M = sum(Judgment=='M')/n(),CR = sum(Judgment=='CR')/n(),
                                                                                         accuracy = sum(accuracy)/n(), 
                                                                                         TPR = (sum(Judgment=='H') / (sum(Judgment=='H') + sum(Judgment=='M'))),
                                                                                         FPR = (sum(Judgment=='FA') / (sum(Judgment=='FA') + sum(Judgment=='CR'))),
                                                                                         group = unique(group),.groups='drop') 

# create a summary rt and accuracy per condition
rt_sum <- task_raw %>% group_by(Condition, Speed, Structure) %>% summarize(mean_logrt = mean(log_rt,na.rm=TRUE), sd_logrt = sd(log_rt,na.rm=TRUE), 
                                                                           mean_rt = mean(rt_cleaned,na.rm=TRUE), sd_rt = sd(rt_cleaned,na.rm=TRUE))

acc_sum <- Rates_all %>% group_by(Condition,Speed, Structure) %>% summarize(m_accuracy = mean(accuracy), sd= sd(accuracy), 
                                                                          TPR = mean(TPR), FPR= mean(FPR), FA= mean(FA), H=mean(H), M = mean(M), CR= mean(CR)) 

# get each participant's basic accuracy across conditions
basic_A <- task_raw%>% group_by(Participant) %>% summarize(FA = sum(Judgment=='FA')/n(), H = sum(Judgment=='H')/n(),
                                                            M = sum(Judgment=='M')/n(),CR = sum(Judgment=='CR')/n(),
                                                            accuracy = sum(accuracy)/n(), 
                                                            TPR = (sum(Judgment=='H') / (sum(Judgment=='H') + sum(Judgment=='M'))),
                                                            FPR = (sum(Judgment=='FA') / (sum(Judgment=='FA') + sum(Judgment=='CR'))))

# ------ Comprehension -----
comprehension <- read_csv(file.path(behavioral_dir, "comp.csv")) %>% filter(Status =='subj') %>%
  pivot_longer(cols=c('scrambled_fast','scrambled_slow',
                      'sents_fast',	'sents_slow',	'intact_fast',	'intact_slow'),
               names_to='Condition',
               values_to='comp')

comp_task <- task_raw %>% group_by(Condition,Speed,Structure,Participant) %>% 
  reframe(accuracy = sum(Judgment %in% c('H','CR'))/n(), group = unique(group)) %>% merge(.,comprehension) %>% group_by(Participant) %>%
  mutate(z_comp = scale(comp)) %>% ungroup() %>% mutate(Speed = factor(Speed,levels = c('Slow', 'Fast')))

comp_summary <- comp_task %>% group_by(Condition,Speed, Structure) %>% summarize(m_comp = mean(z_comp), sd= sd(z_comp)) 
# zscore the comprehension within participant

## Calculate correlation between comprehension and acc
comp_acc <- cor.test(comp_task$accuracy, comp_task$z_comp)
report(comp_acc)
print(paste('There is a ', cor(comp_task$accuracy, comp_task$z_comp), 
            ' correlation between task accuracy and self-reported comprehension!'))
      
# ------ Stats -------

## Comprehension
#assumptions <- comp_task %>% summarize(skew = skewness(accuracy), kurtosis = kurtosis(accuracy))
#print(assumptions)
shapiro.test(comp_task$z_comp)
# Check homogeneity
leveneTest(z_comp ~ Structure*Speed,data = comp_task) # if not significant then we cannot reject the null hyp of equality
# Visualize outliers
boxplot(z_comp ~ Structure*Speed,data = comp_task)

# Reminder of how to interpret
#(-0.5, 0.5): low or approximately symmetric.
#(-1, -0.5) U (0.5, 1): moderately skewed.
#Beyond -1 and 1: Highly skewed.
# Kurtosis should be around 3 

# run the test; look into means parametrization
contrasts(comp_task$Structure) <- contr.treatment
model.comp <- lmer(
  z_comp ~ Structure * Speed + # Fixed Effects: Main effects and interaction
    (1 | Participant) + group,   # Random Intercept: Assumes each participant has a unique baseline accuracy
  data = comp_task
)
summary(model.comp, corr=FALSE)
anova(model.comp)
report(model.comp)

### pairwise testing
m_struc_comp <- emmeans(model.comp, ~ Structure)
m_speed_comp <- emmeans(model.comp, ~ Speed)

comparisons_comp_struc <- as.data.frame(pairs(m_struc_comp))%>% mutate(group1 = str_split(contrast, " - ",, simplify = TRUE)[,1]
                                                                , group2= str_split(contrast, " - ",, simplify = TRUE)[,2], 
                                                                psignif = case_when(
                                                                  p.value <= 0.0001 ~ '****',
                                                                  p.value <= 0.001 ~ '***',
                                                                  p.value <= 0.01 ~ '**',
                                                                  p.value <= 0.05 ~ '*',
                                                                  p.value <= 0.1 ~ '.',))
comparisons_comp_speed <- as.data.frame(pairs(m_speed_comp))%>% mutate(group1 = str_split(contrast, " - ",, simplify = TRUE)[,1]
                                                                , group2= str_split(contrast, " - ",, simplify = TRUE)[,2], 
                                                                psignif = case_when(
                                                                  p.value <= 0.0001 ~ '****',
                                                                  p.value <= 0.001 ~ '***',
                                                                  p.value <= 0.01 ~ '**',
                                                                  p.value <= 0.05 ~ '*',
                                                                  p.value <= 0.1 ~ '.',))

summary(as.glht(pairs(m_struc_comp)), test=adjusted("single-step")) # tukey; just useful for an eyeball interpretation
summary(as.glht(pairs(m_speed_comp)), test=adjusted("single-step")) # tukey; just useful for an eyeball interpretation

### interaction effects
m01 <- emmeans(model.comp, ~ Structure:Speed)

interactionss_comp <- as.data.frame(pairs(m01)) %>%
  mutate(
    group1 = word(str_split(contrast, " - ", simplify = TRUE)[,1], 2, sep = " "),
    group2 = word(str_split(contrast, " - ", simplify = TRUE)[,2], 2, sep = " "),
    # Create two columns that match the actual x & color mapping in ggboxplot
    Structure1 =  word(str_split(contrast, " - ", simplify = TRUE)[,1], 1, sep = " "),
    Structure2 =  word(str_split(contrast, " - ", simplify = TRUE)[,2], 1, sep = " "),
    psignif = case_when(
      p.value <= 0.0001 ~ '****',
      p.value <= 0.001  ~ '***',
      p.value <= 0.01   ~ '**',
      p.value <= 0.05   ~ '*',
      p.value <= 0.1    ~ '.'
    )
  )

# structure centered interactions; simplified table that makes it easier to parse
St_interactions_comp <- interactionss_comp %>%
  filter(group1 == group2, Structure1 != Structure2) %>%
  transmute(Speed = group1, group1 = Structure1, group2= Structure2,y.position = 1.1,
            label = psignif) %>% mutate(Speed = factor(Speed,levels = c('Slow', 'Fast')
            ))

# speed centered interactions; simplified table that makes it easier to parse
Sp_interactions_comp <- interactionss_comp %>%
  filter(Structure1 == Structure2, group1 != group2) %>%
  transmute(Structure = Structure1, group1, group2,y.position = 1.1,
    label = psignif) %>% mutate(Structure = factor(Structure,levels = levels(comp_task$Structure)))


## Accuracy;GLMM
# run the test
contrasts(task_raw$Structure) <- contr.treatment # needed bc r treats ordered factors weird

log_model.acc <- glmer(accuracy ~ Structure * Speed + # Fixed Effects: Main effects and interaction
    (1 | Participant) + (1 | Trial_num) + group,   # Random Intercept: Assumes each participant has a unique baseline accuracy
  data = task_raw, family = binomial()
)

summary(log_model.acc, corr=FALSE)
Anova(log_model.acc) #using car bc regular anova does less well for glmm
report(log_model.acc)

### pairwise testing
m1 <- emmeans(log_model.acc, ~ Structure, type='response')
comparisons_acc <- as.data.frame(pairs(m1)) %>% mutate(group1 = str_split(contrast, " / ",, simplify = TRUE)[,1]
, group2= str_split(contrast, " / ",, simplify = TRUE)[,2], 
psignif = case_when(
  p.value <= 0.0001 ~ '****',
  p.value <= 0.001 ~ '***',
  p.value <= 0.01 ~ '**',
  p.value <= 0.05 ~ '*',
  p.value <= 0.1 ~ '.',), label = psignif)

summary(as.glht(pairs(m1)), test=adjusted("single-step")) # tukey; just useful for an eyeball interpretation

# interactions accuracy

m11 <- emmeans(log_model.acc, ~ Structure:Speed)

interactionss_acc <- as.data.frame(pairs(m11)) %>%
  mutate(
    group1 = word(str_split(contrast, " - ", simplify = TRUE)[,1], 2, sep = " "),
    group2 = word(str_split(contrast, " - ", simplify = TRUE)[,2], 2, sep = " "),
    # Create two columns that match the actual x & color mapping in ggboxplot
    Structure1 =  word(str_split(contrast, " - ", simplify = TRUE)[,1], 1, sep = " "),
    Structure2 =  word(str_split(contrast, " - ", simplify = TRUE)[,2], 1, sep = " "),
    psignif = case_when(
      p.value <= 0.0001 ~ '****',
      p.value <= 0.001  ~ '***',
      p.value <= 0.01   ~ '**',
      p.value <= 0.05   ~ '*',
      p.value <= 0.1    ~ '.'
    )
  )

# structure centered interactions
St_interactions_acc <- interactionss_acc %>%
  filter(group1 == group2, Structure1 != Structure2) %>%
  transmute(Speed = group1, group1 = Structure1, group2= Structure2,y.position = 1.1,
            label = psignif) %>% mutate(Speed = factor(Speed,levels = c('Slow', 'Fast')
            ))

# speed centered interactions
Sp_interactions_acc <- interactionss_acc %>%
  filter(Structure1 == Structure2, group1 != group2) %>%
  transmute(Structure = Structure1, group1, group2,y.position = 1.1,
            label = psignif) %>% mutate(Structure = factor(Structure,levels = levels(task_raw$Structure)))

## Reaction time
# filter the trials to only get correct ones

corr_task <- task_raw %>% filter(accuracy==1)

# run the test; look into means parametrization
contrasts(task_raw$Structure) <- contr.treatment
model.rt <- lmer(
  log_rt ~ Structure * Speed + # Fixed Effects: Main effects and interaction
    (1 | Participant) + (1 | Trial_num) + group,   # Random Intercept: Assumes each participant has a unique baseline accuracy
  data = task_raw
)
summary(model.rt, corr=FALSE)
anova(model.rt)
report(model.rt)

### pairwise testing
m_struc <- emmeans(model.rt, ~ Structure)
m_speed <- emmeans(model.rt, ~ Speed)

comparisons_rt_struc <- as.data.frame(pairs(m_struc))%>% mutate(group1 = str_split(contrast, " - ",, simplify = TRUE)[,1]
                                                                , group2= str_split(contrast, " - ",, simplify = TRUE)[,2], 
                                                                psignif = case_when(
                                                                  p.value <= 0.0001 ~ '****',
                                                                  p.value <= 0.001 ~ '***',
                                                                  p.value <= 0.01 ~ '**',
                                                                  p.value <= 0.05 ~ '*',
                                                                  p.value <= 0.1 ~ '.',))
comparisons_rt_speed <- as.data.frame(pairs(m_speed))%>% mutate(group1 = str_split(contrast, " - ",, simplify = TRUE)[,1]
                                                                , group2= str_split(contrast, " - ",, simplify = TRUE)[,2], 
                                                                psignif = case_when(
                                                                  p.value <= 0.0001 ~ '****',
                                                                  p.value <= 0.001 ~ '***',
                                                                  p.value <= 0.01 ~ '**',
                                                                  p.value <= 0.05 ~ '*',
                                                                  p.value <= 0.1 ~ '.',))

summary(as.glht(pairs(m_struc)), test=adjusted("single-step")) # tukey; just useful for an eyeball interpretation
summary(as.glht(pairs(m_speed)), test=adjusted("single-step")) # tukey; just useful for an eyeball interpretation

# interaction effects
m5 <- emmeans(model.rt, ~ Structure:Speed)

interactionss_rt <- as.data.frame(pairs(m5)) %>%
  mutate(
    group1 = word(str_split(contrast, " - ", simplify = TRUE)[,1], 2, sep = " "),
    group2 = word(str_split(contrast, " - ", simplify = TRUE)[,2], 2, sep = " "),
    # Create two columns that match the actual x & color mapping in ggboxplot
    Structure1 =  word(str_split(contrast, " - ", simplify = TRUE)[,1], 1, sep = " "),
    Structure2 =  word(str_split(contrast, " - ", simplify = TRUE)[,2], 1, sep = " "),
    psignif = case_when(
      p.value <= 0.0001 ~ '****',
      p.value <= 0.001  ~ '***',
      p.value <= 0.01   ~ '**',
      p.value <= 0.05   ~ '*',
      p.value <= 0.1    ~ '.'
    )
  )

# speed centered interactions
Sp_interactions_rt <- interactionss_rt %>%
  filter(Structure1 == Structure2, group1 != group2) %>%
  transmute(Structure = Structure1, group1, group2,
            label = psignif) %>% mutate(Structure = factor(Structure,levels = levels(task_raw$Structure)))


# structure centered interactions
St_interactions_rt <- interactionss_rt %>%
  filter(group1 == group2, Structure1 != Structure2) %>%
  transmute(Speed = group1, group1 = Structure1, group2= Structure2,y.position = 1.1,
            label = psignif) %>% mutate(Speed = factor(Speed,levels = c('Slow', 'Fast')
            ))


# ------- Plotting time -------

# true positives are hits/hits and misses
# false positives are false alarms/ FA and correct rejects
# Use only Arial, Times, or Symbol font in 8-12 point

structure_fill <- c("WordList" = '#efdda9',"SentList" = '#cbcf7e', "Story" = '#b0c885')
speed_outline <- c("Fast" = '#daa6ba', "Slow" = '#74678E')


## Main Paper plots

## boxplot interactions comp
plot_comp <- comp_task %>% group_by(Structure, Speed,Participant) %>%
  summarise(across(z_comp, mean))

c_inter <- ggboxplot(plot_comp, x = "Structure", y = "z_comp", color = "Speed",
                     fill="Structure", ylab= 'Comprehension (z)',
                     group = "Speed", add = "jitter", 
                     xlab= FALSE,add.params = list(size = 0.8)) +
         scale_fill_manual(values = structure_fill) +
         scale_color_manual(values=speed_outline) + 
         stat_pvalue_manual(
                  comparisons_comp_struc,
                  y.position = 1.9, step.increase = 0.08,
                  label = "psignif", 
                       ) + 
theme(text = element_text(family = "Arial"),
                                 legend.position = "none") + coord_cartesian(ylim = c(-2.5,2.5))


# boxplot accuracy - inter
plot_rates <- task_raw %>% group_by(Participant,Structure, Speed) %>%
  summarise(across(everything(), mean))

acc_inter <- ggboxplot(plot_rates, x = "Structure", y = "accuracy", color = "Speed",
            fill="Structure", add = "jitter", ylab= 'Accuracy', 
            xlab= FALSE,add.params = list(size = 0.8)) + 
  scale_fill_manual(values = structure_fill) +
  scale_color_manual(values=speed_outline) + 
  stat_pvalue_manual(
    comparisons_acc,
    y.position = 0.95, step.increase = 0.09,#step.group.by = "Speed",
    label = "label", 
  ) +
  theme(text = element_text(family = "Arial"),
        legend.position = "none") + coord_cartesian(ylim = c(0,1.1))
  
## boxplot interactions rt
plot_rt <- task_raw %>% group_by(Speed, Structure,Participant) %>% summarise(
  across(
    .cols =  !Trial_num, 
    .fns = mean, 
    na.rm = TRUE # Essential: Exclude NA values when calculating the mean
  ),.groups = 'drop')

rt_inter <- ggboxplot(plot_rt, x = "Structure", y = "log_rt", color = "Speed",fun = "mean",
                      fill="Structure", add = "jitter", ylab= 'Reaction Time (log)', 
                      xlab= FALSE, add.params = list(size = 0.8)) + 
  scale_fill_manual(values = structure_fill) +
  scale_color_manual(values=speed_outline) + 
  stat_pvalue_manual(
    comparisons_rt_struc,
    y.position = 8.3, step.increase = 0.1,
    label = "psignif", 
  ) + theme(text = element_text(family = "Arial"),
            legend.position = "none") + coord_cartesian(ylim = c(6.5, 8.5))
  
  


# final plot!!
plot_grid(acc_inter,rt_inter, c_inter, nrow=1, labels = "AUTO") # creates a plot with both infos

## SUPPLEMENTARY PLOTS

# comprehension and accuracy

# plot
ggscatterhist(
  comp_task, x = "accuracy", y = "z_comp",
  color="Structure",
  margin.plot = "boxplot", 
  margin.params = list(fill = "Structure", color = "black", size = 0.2),
  palette = c("#efdda9", "#cbcf7e" ,"#b0c885"),
  xlab = "Accuracy", ylab = 'Comprehension (z)',
  cor.coef=TRUE,font.family = "Public Sans")