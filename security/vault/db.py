import sqlite3


def connect(rows: list[tuple[str, str]]) -> sqlite3.Connection:
    """An in-memory users table (name, role), filled with rows."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE users (name TEXT PRIMARY KEY, role TEXT NOT NULL)")
    conn.executemany("INSERT INTO users VALUES (?, ?)", rows)
    return conn


def find_user(conn: sqlite3.Connection, name: str) -> list[tuple[str, str]]:
    """Users whose name equals `name` exactly. The name is data, never SQL."""
    return conn.execute("SELECT name, role FROM users WHERE name = ?", (name,)).fetchall()
