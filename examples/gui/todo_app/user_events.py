from dataclasses import dataclass
from sqlite3 import Connection
from typing import List, Optional
from pyesys import event
from datetime import datetime

import tkinter as tk
from tkinter import ttk


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


class UserEventView(ttk.Frame):
    def __init__(self, master: tk.Tk):
        super().__init__(master)
        self.pack(fill="both", expand=True, padx=10, pady=10)

        self.__create_widgets()

    def __create_widgets(self):

        # Task Treeview section (with scrollbar)
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, pady=(0, 10))  # Stack at top

        self.event_tree = ttk.Treeview(
            tree_frame, columns=("Date", "Description"), show="headings", height=10
        )

        self.event_tree.heading("Date", text="Date")
        self.event_tree.heading("Description", text="Description")
        self.event_tree.column("Date", width=100)
        self.event_tree.column("Description", width=300)
        self.event_tree.pack(side="left", fill="both", expand=True)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self.event_tree.yview
        )
        self.event_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # Add clear button
        clear_button = ttk.Button(self, text="Clear", command=self.__clear_pressed)
        clear_button.pack(side=tk.LEFT)

    def update_list(self, events: List[UserEvent]):
        self.event_tree.delete(*self.event_tree.get_children())

        for i, event in enumerate(events):
            self.event_tree.insert(
                "", "end", iid=str(i), values=(event.date, event.description)
            )

    @event
    def on_clear_pressed(self):
        """Event fired when the clear button is pressed."""
        ...

    @on_clear_pressed.emitter
    def __clear_pressed(self):
        self.event_tree.selection_remove(self.event_tree.selection())


class UserEventPresenter:
    def __init__(self, model: UserEventRepository, view: UserEventView):
        self.__model = model
        self.__view = view

        # Connect events.
        self.__view.on_clear_pressed += self.__handle_clear_event_list_pressed

        # Display initial tasks
        self.update()

    def update(self):
        self.__view.update_list(self.__model.get_all())

    def __handle_clear_event_list_pressed(self):
        self.__model.clear()
        self.update()

    def log(self, description: str):
        event = UserEvent(
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            description=description,
        )
        self.__model.create(event)
        self.update()


if __name__ == "__main__":
    import sqlite3

    conn = sqlite3.connect(":memory:")

    table_name = "user_events"

    conn.execute(
        f"CREATE TABLE {table_name} (date timestamp NOT NULL, description TEXT NOT NULL)"
    )

    repo = UserEventRepository(conn, "user_events")

    for event in repo.get_all():
        print(event)

    root = tk.Tk()
    root.title("User Event View Component")
    root.geometry("600x400")

    view = UserEventView(root)

    presenter = UserEventPresenter(repo, view)

    presenter.log("First event")
    presenter.log("Second event")
    presenter.log("Third event")

    root.mainloop()
