"""Load shared project paths from project_config.json and environment overrides."""

import json
import os
from pathlib import Path


CONFIG_FILE = Path(__file__).resolve().with_name("project_config.json")


def _load_config():
    """Read the project's JSON path configuration."""
    with CONFIG_FILE.open(encoding="utf-8") as config_file:
        return json.load(config_file)


def get_path(name):
    """Return a configured path, optionally overridden by an environment variable.

    Set PROJECT_ROOT for the dataset/project root or
    STRUCTURE_SPEED_PATH_<NAME> to override an individual configured path.
    Relative paths are resolved against the configured project root.
    """
    config = _load_config()
    root_value = os.environ.get(
        "PROJECT_ROOT", config.get("project_root", ".")
    )
    root = Path(root_value).expanduser()
    if not root.is_absolute():
        root = (CONFIG_FILE.parent / root).resolve()

    if name == "project_root":
        return root

    env_name = f"STRUCTURE_SPEED_PATH_{name.upper()}"
    path_value = os.environ.get(env_name, config.get("paths", {}).get(name))
    if path_value is None:
        raise KeyError(f"No project path is configured for {name!r}")

    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = root / path
    return path
