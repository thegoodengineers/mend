"""Path traversal and broken access control: the feature works, and the exploit does not."""

import pytest

from vault.files import read_note
from vault.notes import NoteStore


def test_read_note_inside_the_folder(tmp_path):
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "todo.txt").write_text("buy milk", encoding="utf-8")
    (tmp_path / "notes" / "sub").mkdir()
    (tmp_path / "notes" / "sub" / "a.txt").write_text("nested", encoding="utf-8")
    assert read_note(str(tmp_path / "notes"), "todo.txt") == "buy milk"
    assert read_note(str(tmp_path / "notes"), "sub/a.txt") == "nested"


def test_exploit_path_traversal_is_rejected(tmp_path):
    (tmp_path / "notes").mkdir()
    (tmp_path / "secret.txt").write_text("db password", encoding="utf-8")
    for name in ("../secret.txt", "sub/../../secret.txt", str(tmp_path / "secret.txt")):
        with pytest.raises(ValueError):
            read_note(str(tmp_path / "notes"), name)


def test_owner_and_admin_can_delete():
    store = NoteStore(admins={"alice"})
    a = store.add("bob", "mine")
    b = store.add("carol", "hers")
    store.delete("bob", a)
    store.delete("alice", b)
    assert store.notes == {}


def test_exploit_other_user_cannot_delete():
    store = NoteStore(admins={"alice"})
    note = store.add("carol", "private")
    with pytest.raises(PermissionError):
        store.delete("bob", note)
    assert note in store.notes
