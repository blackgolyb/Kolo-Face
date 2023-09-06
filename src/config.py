from pathlib import Path
from platformdirs import user_config_dir

PROJECT_FOLDER = Path(__file__).resolve().parent.parent
RESOURCES_FOLDER = PROJECT_FOLDER / "resources"
CONFIG_FILE = Path(user_config_dir()) / "config.ini"
