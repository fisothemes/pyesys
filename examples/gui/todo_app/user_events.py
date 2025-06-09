from dataclasses import dataclass
from sqlite3 import Connection
from typing import List, Optional


@dataclass
class UserEvent:
    date: str
    description: str


class UserEventRepository:
    def __init__(self, conn: Connection, table: str):
        self.conn = conn
        self.table = table

    def get_all(self) -> List[UserEvent]:
        cur = self.conn.execute(f"SELECT * FROM {self.table}")
        return [UserEvent(*row) for row in cur.fetchall()]

    def create(self, event: UserEvent) -> None:
        with self.conn:
            self.conn.execute(
                f"INSERT INTO {self.table} VALUES (?, ?)",
                (
                    event.date,
                    event.description,
                ),
            )

    def read_by_row_index(self, index: int) -> Optional[UserEvent]:
        row = self.conn.execute(
            f"SELECT * FROM {self.table} WHERE rowid=?", (index + 1,)
        ).fetchone()

        return UserEvent(*row) if row else None

    def delete(self, index: int) -> None:
        with self.conn:
            self.conn.execute(f"DELETE FROM {self.table} WHERE rowid=?", (index + 1,))

    def clear(self) -> None:
        with self.conn:
            self.conn.execute(f"DELETE FROM {self.table}")

if __name__ == "__main__":
    import sqlite3

    conn = sqlite3.connect(":memory:")

    conn.execute(
        """CREATE TABLE user_events (
        date TEXT NOT NULL,
        description TEXT NOT NULL
    )"""
    )

    repo = UserEventRepository(conn, "user_events"),

    sample_events = [
        UserEvent(date="2023-01-01", description="Test event"),
        UserEvent(date="2023-01-02", description="Test event 2")
    ]

    for event in sample_events:
        repo.create(event)

    for event in repo.get_all():
        print(event)

    print(f"\n{repo.read_by_row_index(1)}\n")

    repo.delete(0)

    for event in repo.get_all():
        print(event)
