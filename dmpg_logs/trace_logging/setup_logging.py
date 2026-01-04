import json
import logging.config
import logging.handlers
import pathlib
import datetime as dt

from dmpg_logs.logging_utils.file_logger import log_puffer_dict, find_puffer_path
from dmpg_logs.logging_utils.gps_logger import find_gps_path, log_gps_json_dict


def setup_logging(log_puffer: bool = False, log_gps: bool = False):
    base_dir = pathlib.Path(__file__).resolve().parent.parent
    config_path = base_dir / "trace_logging" / "logging_configs.json"
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    now = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file_name = f"dmpg_{now}.log"
    log_file_path = base_dir / "logs" / log_file_name
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    if log_puffer:
        puffer_path = find_puffer_path(base_dir)
        log_puffer_dict(log_file_path, puffer_path if puffer_path else base_dir / "puffer.py")

    if log_gps:
        gps_path = find_gps_path(base_dir)
        if gps_path:
            log_gps_json_dict(log_file_path, gps_path)
        else:
            with log_file_path.open("a" if log_file_path.exists() else "w", encoding="utf-8") as f:
                f.write("# no GPS JSON file found (dmpg_logs/ or DMPG_GPS_JSON)\n\n")

    h = config.setdefault("handlers", {}).setdefault("file", {})
    h["filename"] = str(log_file_path)
    h["class"] = "logging.FileHandler"
    h["mode"] = "a"
    h.setdefault("encoding", "utf-8")
    h.pop("maxBytes", None)
    h.pop("backupCount", None)

    logging.config.dictConfig(config)
