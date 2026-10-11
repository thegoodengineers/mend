ALLOWED = {".png", ".jpg", ".jpeg", ".gif", ".pdf"}


def allowed_file(filename: str) -> bool:
    """Accept an upload only if its final extension is on the allow-list (case-insensitive)."""
    name = filename.strip().lower()
    dot = name.rfind(".")
    return dot > 0 and name[dot:] in ALLOWED
