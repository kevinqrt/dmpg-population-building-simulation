from __future__ import annotations
import pathlib
from typing import Optional

DEFAULT_GPS_DIRNAME = "dmpg_logs"
DEFAULT_GPS_FILENAME = "gps_data.JSON"


def find_gps_path(base_dir: pathlib.Path) -> Optional[pathlib.Path]:
    """
    Finds gps_data.JSON in dmpg_logs directory.
    The file is always located at: dmpg_logs/gps_data.JSON
    """
    # Check: base_dir/dmpg_logs/gps_data.JSON
    gps_path = base_dir / DEFAULT_GPS_DIRNAME / DEFAULT_GPS_FILENAME
    if gps_path.is_file():
        return gps_path

    # If base_dir itself is dmpg_logs: dmpg_logs/gps_data.JSON
    if base_dir.name.lower() == DEFAULT_GPS_DIRNAME:
        gps_path = base_dir / DEFAULT_GPS_FILENAME
        if gps_path.is_file():
            return gps_path

    return None


def log_gps_json_dict(log_file: pathlib.Path, json_path: pathlib.Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if log_file.exists() else "w"

    try:
        with json_path.open("r", encoding="utf-8") as src, log_file.open(mode, encoding="utf-8") as dst:
            dst.write(f"# ---- gps_json: {json_path} ----\n")
            last = ""
            for line in src:
                dst.write(line)
                last = line
            if last and not last.endswith("\n"):
                dst.write("\n")
            dst.write("\n")
    except FileNotFoundError:
        with log_file.open(mode, encoding="utf-8") as f:
            f.write(f"# gps json not found at: {json_path}\n\n")
    except Exception as ex:
        with log_file.open(mode, encoding="utf-8") as f:
            f.write("# gps json found but could not be logged\n")
            f.write(f"# error: {ex}\n\n")
