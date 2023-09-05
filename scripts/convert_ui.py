from pathlib import Path
from os import system

from scripts.blackify import blackify


project_folder = Path(__file__).resolve().parent.parent
ui_folder = project_folder / "ui"
python_ui_folder = project_folder / "src/ui"


def convert_file(input_file, output_file):
    system(f"pyuic5 {input_file} -o {output_file}")


def prepare_file_name(file):
    return f"{file.stem}.py"


def validate_edit_replace(file_path):
    with file_path.open() as file:
        data = file.read()

    data = "from widgets.validate_edit import VelidateLineEdit\n" + data

    divider = "self.divider = "
    data = data.replace(f"{divider}QtWidgets.QLineEdit", f"{divider}VelidateLineEdit")
    color_shift = "self.color_shift = "
    data = data.replace(
        f"{color_shift}QtWidgets.QLineEdit", f"{color_shift}VelidateLineEdit"
    )

    with file_path.open(mode="w") as file:
        file.write(data)


def extra(python_ui_folder):
    file_names_for_replace = [
        "filter_creator.py",
    ]

    for ui_file in python_ui_folder.iterdir():
        if ui_file.name in file_names_for_replace:
            validate_edit_replace(ui_file)


def convert_ui_file_to_python():
    if not python_ui_folder.exists():
        return

    if not ui_folder.exists():
        return

    for ui_file in ui_folder.iterdir():
        if not ui_file.is_file():
            continue

        if ui_file.suffix != ".ui":
            continue

        output_file = python_ui_folder / prepare_file_name(ui_file)
        convert_file(ui_file, output_file)

    extra(python_ui_folder)
    blackify(python_ui_folder)


if __name__ == "__main__":
    convert_ui_file_to_python()
