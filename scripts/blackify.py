from pathlib import Path
from os import system


project_folder = Path(__file__).resolve().parent.parent
src_folder = project_folder / "src"


def blackify(folder=src_folder):
    system(f"black {folder}")
