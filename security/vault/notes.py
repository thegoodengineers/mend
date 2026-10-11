class NoteStore:
    """Notes owned by users. Only the owner, or an admin, may delete a note."""

    def __init__(self, admins: set[str]):
        self.admins = set(admins)
        self.notes: dict[int, dict] = {}
        self._next = 1

    def add(self, owner: str, text: str) -> int:
        note_id, self._next = self._next, self._next + 1
        self.notes[note_id] = {"owner": owner, "text": text}
        return note_id

    def delete(self, user: str, note_id: int) -> None:
        note = self.notes[note_id]
        if user != note["owner"] and user not in self.admins:
            raise PermissionError(f"{user} may not delete note {note_id}")
        del self.notes[note_id]
