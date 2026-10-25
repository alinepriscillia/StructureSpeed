project_dir <- normalizePath(file.path(dirname(script_file), ".."), mustWork = TRUE)
source(file.path(project_dir, "project_config.R"))

setwd(get_project_path("behavioral_raw"))
res_dir = "preproc"

library(ggplot2)
library(RColorBrewer)
library(VWPre)
library(ggpubr)
library(dplyr)
library(readr)
library(formattable)
library(tidyr)
library(stringr)
library(tidyverse)


options(scipen=999)

# ------------------------------- Load file function --------------------------------------
read.pcibex <- function(filepath, auto.colnames=TRUE, fun.col=function(col,cols){cols[cols==col]<-paste(col,"Ibex",sep=".");return(cols)}) {
  n.cols <- max(count.fields(filepath,sep=",",quote=NULL),na.rm=TRUE)
  if (auto.colnames){
    cols <- c()
    con <- file(filepath, "r")
    while ( TRUE ) {
      line <- readLines(con, n = 1, warn=FALSE)
      if ( length(line) == 0) {
        break
      }
      m <- regmatches(line,regexec("^# (\\d+)\\. (.+)\\.$",line))[[1]]
      if (length(m) == 3) {
        index <- as.numeric(m[2])
        value <- m[3]
        if (is.function(fun.col)){
          cols <- fun.col(value,cols)
        }
        cols[index] <- value
        if (index == n.cols){
          break
        }
      }
    }
    close(con)
    return(read.csv(filepath, comment.char="#", header=FALSE, col.names=cols, colClasses=c('character'), quote=""))
  }
  else{
    return(read.csv(filepath, comment.char="#", header=FALSE, col.names=seq(1:n.cols)))
  }
}
# ----------------- Settings for analysis -----------------

# Settings for eliminating participants; might change this
criteria.badtask = 0.5
criteria.rt.max = 5000
criteria.rt.min = 200
criteria.comp = 0.2
bad_par.prof = "678e71a80cca3c2468ca252a" # for some reason won't save

# --------------- Read in file -----------------
corpus_results <-
  list.files(pattern = "\\.csv$") %>% map_dfr(~read.pcibex(.)) 

# Set anything empty to NA
corpus_results[corpus_results==""] <- NA

#Filter df to be more readable and drop pilot/demos
results <- corpus_results %>% dplyr::select(Label, PennElementName,ID,Parameter, 
                Value, EventTime, trialnum, length, stim, match,type, story, Comments, stim) %>% 
                  mutate_at(c('EventTime', 'trialnum', 'length'), as.numeric) %>% 
                drop_na(ID) %>% mutate_at(c('match'), as.logical)

# I fucked up and didn't read the IDs in correctly and this fixes that
results <- results %>% mutate(prolific_id = NA) %>%  # Create a new column for real IDs
  mutate(prolific_id = ifelse(grepl("prolificid", Label), stim, NA)) %>%  # Extract IDs from stim
  fill(prolific_id, .direction = "down")  # Fill the ID down for all rows

# get reaction time values
results <- results %>% mutate(reaction_time = c(0, diff(EventTime)))

# Get number of participants and double check something isn't being cut
n_par = length(unique(results$prolific_id))
print(n_par)

# -------- Identify bad par based on task response accuracy and reaction time----------
setwd(get_project_path("stimulus_task"))

# get the csvs for the tasks to map on the right responses
task_csvs <- list.files(pattern = "\\.csv$") %>% 
  map_dfr(~read_csv(., id = "name")) %>%
  mutate(
    story = case_when(
      grepl("story3", name) ~ "story3",
      grepl("story2", name) ~ "story2",
      TRUE ~ NA_character_
    ),
    type = case_when(
      grepl("intact", name) ~ "intact",
      grepl("scram", name) ~ "scrambled_words",
      grepl("chunks", name) ~ "scrambled_chunks",
      TRUE ~ NA_character_
    )
  )

# isolate the task responses
task_resp <- results %>% filter(grepl(('task1|task2'),Label) & grepl("PressedKey", Parameter))  %>%
  rename(cnum = trialnum, clen = length, chunk = stim) %>% 
  mutate(chunk = gsub("%2C", ",", chunk)) %>% mutate(speed = case_when(grepl("1",Label) ~"fast",
                                                                       grepl("2",Label) ~"slow"))

# map the right responses because the data collection was messy
clean_task <- task_resp %>% group_by(prolific_id) %>%
  left_join(
    task_csvs %>%
      select(match, story, type, cnum, clen, chunk),  # Select necessary columns from task_csvs
    by = c("story", "type", "cnum", "clen", "chunk")   # Perform the merge across all columns
  ) %>% mutate(match = match.y) %>% select(-match.x, -match.y)  # Remove old match columns


# calculate the accuracies
clean_task <- clean_task %>% mutate(accuracy = case_when(match == TRUE & Value == 'F' ~ 1,
                                                       match == FALSE & Value == 'J' ~ 1,
                                                       .default = 0), 
                                  response = case_when(match == TRUE & Value == 'F' ~ 'H',
                                                       match == FALSE & Value == 'J' ~ 'CR',
                                                       match == TRUE & Value == 'J' ~ 'M',
                                                       match == FALSE & Value == 'F' ~ 'FA'))

clean_task <- clean_task%>% select(-c(ID, PennElementName, Parameter,Value, EventTime, Comments)) #%>% filter(reaction_time < criteria.rt.max) %>% filter(reaction_time > criteria.rt.min)
# get a measure of how many trials per participant were removed? 

# get a summary of the task accuracy and rt by participant and exclude ppl who drag
task_sum <- clean_task %>% group_by(prolific_id) %>% summarise(mean_acc = mean(accuracy), mean_rt = mean(reaction_time), per.left = n()/180)
boxplot(task_sum$mean_rt, xlab = 'Participants', ylab = 'Reaction time') # basic outlier plot
rtoutlier.par <- task_sum$prolific_id[task_sum$mean_rt %in% boxplot(task_sum$mean_rt)$out & task_sum$mean_rt> criteria.rt.max | task_sum$mean_rt< criteria.rt.min] # reaction time outliers

# get bad participants at task
bad_task.par <- task_sum %>% filter(mean_acc < criteria.badtask) %>% pull(prolific_id) 


# -------- Get comprehension stats ----------
results[results==""] <- NA # again bc this is fucking up my fill

# fill in missing values, filter comprehension and select responses 
comp <- results %>% mutate(speed = case_when(grepl("fast",Label) ~"fast",
      grepl("slow",Label) ~"slow")) %>%  fill(story,type,speed, .direction = "down") %>%
      filter(Label=="comprehension" & Parameter== "Choice") %>%
  select(prolific_id, speed, story, type, Value) 

comp <- comp %>% mutate(Value = as.numeric(Value)) %>%  # Convert Value column to numeric
  mutate( value_recoded = if_else(row_number() <= 143, Value / 99, Value / 6)) %>% mutate(value_recoded = as.numeric(value_recoded))

# get summary stats
comp_sum <- group_by(comp, prolific_id, type) %>% summarise(mean= mean(value_recoded)) %>% ungroup()
# and bad participants 
bad_comp.par <- comp_sum %>% filter(type=='intact') %>% filter(mean < criteria.comp) %>% pull(prolific_id) 

# ---------------- Isolate the personal experience  ----------------
# add a lot of info that has been missing
pexp <- results %>% mutate(speed = case_when(grepl("fast",Label) ~"fast",
                grepl("slow",Label) ~"slow")) %>% fill(story,type,
                speed, .direction = "down") %>% filter(Label=='personal_experience'& Parameter== "Final") %>% 
                select(prolific_id, speed, story, Value, PennElementName) %>%
                mutate(Value = gsub("%2C", ",", Value), Value = gsub("%0A", ",", Value)) # change the commas to commas


# ---------------- Save all the documents ----------------

# !!!!add moment to remove all bad participants before continuing here!!!!
bad_pars <- c(bad_task.par,rtoutlier.par, bad_comp.par, bad_par.prof)
final_task <- clean_task %>% filter(!prolific_id%in% bad_pars)
final_comp <- comp %>% filter(!prolific_id%in% bad_pars)

# save!!
setwd(get_project_path("behavioral"))
write_csv(final_task, paste0('preproc/','recog_task.csv'))
write_csv(final_comp, paste0('preproc/','comprehension.csv'))
# bad participants
fname = "bad.par_allbehav.RData"
save(bad_pars, paste0('preproc/',fname))
#p_exp
write_csv(pexp, paste0('preproc/','p_expresponses.csv'))

#---------------easy ROC -----------------
setwd(get_project_path("behavioral"))
final_task <- read_csv(paste0('preproc/','recog_task.csv'))
