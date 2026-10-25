project_dir <- normalizePath(file.path(dirname(script_file), ".."), mustWork = TRUE)
source(file.path(project_dir, "project_config.R"))

library(tidyverse)
library(ggplot2)
library(ggpubr)
library(multcomp)
library(effectsize)
library("stringr")


# ----------------- Initial set-up --------------- 

setwd(get_project_path("stimuli"))

story2 <- read.csv('story2_final_stim.csv') %>% mutate(num_w = str_count(chunk ,"\\w+"))
story3 <- read.csv('story3_final_stim.csv') %>% mutate(num_w = str_count(chunk ,"\\w+"))

story2scrambled <- read.csv('story2_scrambled.csv') %>% mutate(num_w = str_count(chunk ,"\\w+"))
story3scrambled <- read.csv('story3_scrambled.csv') %>% mutate(num_w = str_count(chunk ,"\\w+"))

# add all of the stories together
storylengths <- story2%>% dplyr::select(clen,num_w,cnum)%>%  mutate(story ="story2", scram = FALSE) %>% rbind(
  story3 %>% dplyr::select(clen,num_w,cnum)%>%  
    mutate(story ="story3", scram = FALSE)) %>%
  rbind(story2scrambled %>% dplyr::select(clen,num_w,cnum) %>%
          mutate(story ="story2", scram = TRUE)) %>%
  rbind(story3scrambled %>% dplyr::select(clen,num_w,cnum)%>%  mutate(story ="story3", scram = TRUE))

summary <- storylengths %>% group_by(story,scram) %>% summarise(mean.length = mean(clen), 
                                                                sd.length = sd(clen), mean.w = mean(num_w), sd.w = sd(num_w))

storylengths$story <- as.factor(storylengths$story)
storylengths$scram <- as.factor(storylengths$scram)


# run an anova to see if an effect
model <- aov(num_w ~ story*scram, storylengths) # anova on all resp not collapsed
summary(model)

model_char <- aov(clen ~ story*scram, storylengths) # anova on all resp not collapsed
summary(model_char)

post_test <- glht(model_char, linfct = mcp(story = "Tukey"))
summary(post_test)
post_test <- glht(model_char, linfct = mcp(scram = "Tukey"))
summary(post_test)

post_test <- glht(model, linfct = mcp(story = "Tukey"))
summary(post_test)
post_test <- glht(model, linfct = mcp(scram = "Tukey"))
summary(post_test)

eta_squared(model)

# ----------------- Plot the differences--------------

storylengths %>% ggplot(aes(x = story, y=clen)) + geom_boxplot()

# -------- Visual angle math ----------

setwd(get_project_path("visual_angle"))

files <- list.files(pattern = "*\\.csv$", full.names = TRUE, recursive = FALSE) %>%
  map_dfr(~ read_csv(.x, quote = '"'))

summary(files)
sd(files$deg)
