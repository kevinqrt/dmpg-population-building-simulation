import json
import pathlib
import os
import importlib.util
import itertools


def log_puffer_dict(log_file: pathlib.Path, puffer_path: pathlib.Path) -> None:
    """Write parsed puffer.py storage_locations to log file header."""
    try:
        text = puffer_path.read_text(encoding="utf-8")
        ns = {}
        exec(text, ns)
        storage_locations = ns.get("storage_locations")

        with log_file.open("w", encoding="utf-8") as f:
            if storage_locations:
                f.write("# ---- storage_locations ----\n")
                json.dump(storage_locations, f, ensure_ascii=False, indent=2, default=str)
                f.write("\n\n")
            else:
                f.write("# puffer.py found but no storage_locations\n\n")

    except FileNotFoundError:
        with log_file.open("w", encoding="utf-8") as f:
            f.write(f"# puffer.py not found at: {puffer_path}\n\n")
    except Exception:
        with log_file.open("w", encoding="utf-8") as f:
            f.write("# puffer.py found but could not parse\n\n")


def find_puffer_path(base_dir: pathlib.Path) -> pathlib.Path | None:
    """
    Find puffer.py file using multiple strategies.
    """
    # Environment variable
    env_path = os.environ.get("DMPG_PUFFER_FILE")
    if env_path and pathlib.Path(env_path).exists():
        return pathlib.Path(env_path)

    # Common project locations
    candidates = [
        base_dir / "puffer.py",
        base_dir.parent / "puffer.py",
        base_dir / "data" / "puffer.py",
        base_dir.parent / "data" / "puffer.py",
    ]

    for path in candidates:
        if path.exists():
            return path

    # Module resolution (pip/package)
    try:
        spec = importlib.util.find_spec("puffer")
        if spec and spec.origin and pathlib.Path(spec.origin).exists():
            return pathlib.Path(spec.origin)
    except Exception:
        pass

    # Limited recursive search
    for directory in itertools.islice([base_dir] + list(base_dir.parents), 3):
        try:
            found = next((p for p in directory.rglob("puffer.py") if p.is_file()), None)
            if found:
                return found
        except Exception:
            continue

    return None
