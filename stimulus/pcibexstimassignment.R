source(file.path(project_dir, "project_config.R"))

library(tidyr)
setwd(get_project_path("logs"))

set.seed(123)

n_stim <- 537 
n_rep <- 5
n_participants <- 80
k_max <- 35 

# Create vector with each stimulus repeated 5 times
stim_assignments <- rep(1:n_stim, n_rep)

# Initialize list of participant assignments
participant_lists <- vector("list", n_participants)

# Initialize empty lists
for(i in 1:n_participants) participant_lists[[i]] <- integer(0)

# Shuffle stim list
stim_list <- sample(stim_assignments)

# Assign stimuli ensuring no duplicates per participant
for (stim in stim_list) {
  # Find participants who do not yet have this stim and have room
  candidates <- which(sapply(participant_lists, function(x) !(stim %in% x) && length(x) < k_max))
  
  # Randomly select one candidate
  if (length(candidates) == 0) stop("No participants available for stimulus assignment")
  chosen <- sample(candidates, 1)
  
  # Assign stim to chosen participant
  participant_lists[[chosen]] <- c(participant_lists[[chosen]], stim)
}

df <- tibble(participant = 1:length(participant_lists),
             stim_list = participant_lists, story = 'story2')

df$order <- sapply(df$stim_list, toString)
write.csv(df[, c("participant", "order", 'story')], "stim_order_story2.csv", row.names=FALSE)

n_stim <-458
n_rep <- 5
n_participants <- 80
k_max <- 29

# Create vector with each stimulus repeated 5 times
stim_assignments <- rep(1:n_stim, n_rep)

# Initialize list of participant assignments
participant_lists <- vector("list", n_participants)

# Initialize empty lists
for(i in 1:n_participants) participant_lists[[i]] <- integer(0)

# Shuffle stim list
stim_list <- sample(stim_assignments)

# Assign stimuli ensuring no duplicates per participant
for (stim in stim_list) {
  # Find participants who do not yet have this stim and have room
  candidates <- which(sapply(participant_lists, function(x) !(stim %in% x) && length(x) < k_max))
  
  # Randomly select one candidate
  if (length(candidates) == 0) stop("No participants available for stimulus assignment")
  chosen <- sample(candidates, 1)
  
  # Assign stim to chosen participant
  participant_lists[[chosen]] <- c(participant_lists[[chosen]], stim)
}

df2 <- tibble(participant = 1:length(participant_lists),
             stim_list = participant_lists, story = 'story3')

df2$order <- sapply(df2$stim_list, toString)
write.csv(df2[, c("participant", "order", 'story')], "stim_order_story3.csv", row.names=FALSE)
