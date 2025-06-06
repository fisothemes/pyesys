from models import ToDoItem, ToDoItemStatus, UserEvent
from typing import List, Union
from sqlite3 import Connection


class ToDoItemRepository:
    def __init__(self, conn: Connection, table: str):
        self.conn = conn
        self.table = table

    def get_all(self) -> List[ToDoItem]:
        cur = self.conn.execute(f"SELECT * FROM {self.table}")
        return [ToDoItem(*row) for row in cur.fetchall()]

    def create(self, item: ToDoItem) -> None:
        self.conn.execute(
            f"INSERT INTO {self.table} VALUES (?, ?, ?)",
            (item.id, item.task, item.status,)
        )
        self.conn.commit()

    def update(self, item: ToDoItem) -> None:
        self.conn.execute(
            f"UPDATE {self.table} SET task=?, status=? WHERE id=?",
            (item.task, item.status, item.id),
        )
        self.conn.commit()

    def read_by_id(self, id: int) -> Union[ToDoItem, None]:
        cur = self.conn.execute(f"SELECT * FROM {self.table} WHERE id=?", (id,))
        row = cur.fetchone()
        return ToDoItem(*row) if row else None

    def read_by_status(self, status: ToDoItemStatus) -> List[ToDoItem]:
        cur = self.conn.execute(f"SELECT * FROM {self.table} WHERE status=?", (status,))
        return [ToDoItem(*row) for row in cur.fetchall()]

    def delete(self, id: int) -> None:
        self.conn.execute(f"DELETE FROM {self.table} WHERE id=?", (id,))
        self.conn.commit()


class UserEventRepository: ...


if __name__ == "__main__":
    import sqlite3

    conn = sqlite3.connect(":memory:")

    conn.execute(
        """CREATE TABLE todo_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task TEXT NOT NULL,
        status INTEGER NOT NULL
    )"""
    )

    conn.execute(
        """CREATE TABLE user_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        description TEXT NOT NULL
    )"""
    )

    todo_repo = ToDoItemRepository(conn=conn, table="todo_items")

    todo_repo.create(
        ToDoItem(id=1, task="Buy groceries", status=ToDoItemStatus.PENDING)
    )
    todo_repo.create(
        ToDoItem(id=2, task="Buy groceries", status=ToDoItemStatus.PENDING)
    )

    print(f"\n{todo_repo.read_by_id(1)}\n")

    todo_repo.update(
        ToDoItem(id=1, task="Buy groceries", status=ToDoItemStatus.COMPLETED)
    )

    for item in todo_repo.get_all():
        print(item)
