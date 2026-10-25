if (!requireNamespace("jsonlite", quietly = TRUE)) {
  stop("The 'jsonlite' R package is required to read project_config.json.")
}

config_file <- local({
  source_file <- tryCatch(sys.frame(1)$ofile, error = function(e) NULL)
  if (is.null(source_file) || !nzchar(source_file)) {
    script_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
    if (length(script_arg)) {
      source_file <- sub("^--file=", "", script_arg[[1]])
    } else {
      source_file <- getwd()
    }
  }

  start_dir <- normalizePath(dirname(source_file), mustWork = FALSE)
  candidates <- file.path(start_dir, "project_config.json")
  candidates <- c(candidates, file.path(start_dir, "..", "project_config.json"))
  candidates <- c(candidates, file.path(getwd(), "project_config.json"))
  candidates <- normalizePath(candidates, mustWork = FALSE)
  found <- candidates[file.exists(candidates)]
  if (!length(found)) {
    stop("Could not locate project_config.json from ", start_dir)
  }
  found[[1]]
})

project_config <- jsonlite::fromJSON(config_file, simplifyVector = FALSE)

get_project_path <- function(name) {
  root_override <- Sys.getenv("PROJECT_ROOT", unset = "")
  root_value <- if (nzchar(root_override)) {
    root_override
  } else {
    project_config$project_root
  }

  if (grepl("^(/|[A-Za-z]:[/\\\\])", root_value)) {
    root <- path.expand(root_value)
  } else {
    root <- file.path(dirname(config_file), path.expand(root_value))
  }
  root <- normalizePath(root, mustWork = FALSE)

  if (identical(name, "project_root")) {
    return(root)
  }

  env_name <- paste0("STRUCTURE_SPEED_PATH_", toupper(name))
  path_value <- Sys.getenv(env_name, unset = "")
  if (!nzchar(path_value)) {
    path_value <- project_config$paths[[name]]
  }
  if (is.null(path_value) || !nzchar(path_value)) {
    stop("No project path is configured for '", name, "'.")
  }

  path_value <- path.expand(path_value)
  if (grepl("^(/|[A-Za-z]:[/\\\\])", path_value)) {
    return(normalizePath(path_value, mustWork = FALSE))
  }
  normalizePath(file.path(root, path_value), mustWork = FALSE)
}
