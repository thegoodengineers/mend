from pathlib import Path


def read_note(base_dir: str, name: str) -> str:
    """Read a note stored under base_dir. Names that point outside base_dir are rejected with ValueError."""
    base = Path(base_dir).resolve()
    target = (base / name).resolve()
    if target != base and base not in target.parents:
        raise ValueError(f"note outside the notes folder: {name}")
    return target.read_text(encoding="utf-8")
