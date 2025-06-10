from enum import StrEnum, auto
from dataclasses import dataclass, astuple
from sqlite3 import Connection
from typing import List, Optional, Tuple
from pyesys import event

import tkinter as tk
from tkinter import ttk, messagebox


class TaskStatus(StrEnum):
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"


@dataclass(eq=True, slots=True)
class Task:
    task: str
    status: TaskStatus = TaskStatus.PENDING


class TaskRepository:
    def __init__(self, conn: Connection, table: str):
        self.conn = conn
        self.table = table

    def get_all(self) -> List[Task]:
        cur = self.conn.execute(f"SELECT * FROM {self.table}")
        return [Task(*row) for row in cur.fetchall()]

    def create(self, item: Task) -> None:
        with self.conn:
            self.conn.execute(
                f"INSERT INTO {self.table} VALUES (?, ?)",
                (
                    item.task,
                    item.status,
                ),
            )

    def update(self, index: int, item: Task) -> None:
        with self.conn:
            self.conn.execute(
                f"UPDATE {self.table} SET task=?, status=? WHERE rowid=?",
                (
                    item.task,
                    item.status,
                    index + 1,
                ),
            )

    def update_status(self, index: int, status: TaskStatus) -> None:
        with self.conn:
            self.conn.execute(
                f"UPDATE {self.table} SET status=? WHERE rowid=?",
                (
                    status,
                    index + 1,
                ),
            )

    def update_task(self, index: int, task: str) -> None:
        with self.conn:
            self.conn.execute(
                f"UPDATE {self.table} SET task=? WHERE rowid=?",
                (
                    task,
                    index + 1,
                ),
            )

    def read_by_row_index(self, index: int) -> Optional[Task]:
        row = self.conn.execute(
            f"SELECT * FROM {self.table} WHERE rowid=?", (index + 1,)
        ).fetchone()

        return Task(*row) if row else None

    def read_by_status(self, status: TaskStatus) -> List[Task]:
        cur = self.conn.execute(f"SELECT * FROM {self.table} WHERE status=?", (status,))
        return [Task(*row) for row in cur.fetchall()]

    def read_task_count(self) -> Optional[int]:
        cur = self.conn.execute(f"SELECT COUNT(*) FROM {self.table}")
        return cur.fetchone()[0] if cur else None

    def delete(self, index: int) -> None:
        with self.conn:
            self.conn.execute(f"DELETE FROM {self.table} WHERE rowid=?", (index + 1,))

    def clear(self) -> None:
        with self.conn:
            self.conn.execute(f"DELETE FROM {self.table}")


class TaskView(ttk.Frame):
    def __init__(self, master: tk.Tk):
        super().__init__(master)
        self.pack(fill="both", expand=True, padx=10, pady=10)

        self.__selected_index: int = -1

        self.__create_widgets()

    def __create_widgets(self):

        # Task Treeview section (with scrollbar)
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, pady=(0, 10))  # Stack at top

        self.task_tree = ttk.Treeview(
            tree_frame, columns=("Task", "Status"), show="headings", height=10
        )
        self.task_tree.heading("Task", text="Task")
        self.task_tree.heading("Status", text="Status")
        self.task_tree.column("Task", width=300)
        self.task_tree.column("Status", width=100)
        self.task_tree.bind("<<TreeviewSelect>>", self._task_selected)
        self.task_tree.pack(side="left", fill="both", expand=True)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self.task_tree.yview
        )
        self.task_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # Input section (LabelFrame with Entry + Combobox)
        input_frame = ttk.LabelFrame(self, text="Task Details", padding="5")
        input_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(input_frame, text="Task:").grid(row=0, column=0, sticky="w")
        self.task_entry = ttk.Entry(input_frame, width=40)
        self.task_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        ttk.Label(input_frame, text="Status:").grid(row=0, column=2, sticky="w")
        self.status_combo = ttk.Combobox(input_frame, width=15, state="readonly")
        self.status_combo["values"] = [e for e in TaskStatus]
        self.status_combo.set(TaskStatus.PENDING)
        self.status_combo.grid(row=0, column=3, sticky="w")

        input_frame.columnconfigure(1, weight=1)

        # Button section (Add/Update/Delete)
        button_frame = ttk.Frame(self)
        button_frame.pack(fill="x")

        self.add_button = ttk.Button(
            button_frame, text="Add", state="normal", command=self._add_task_pressed
        )
        self.add_button.pack(side="left", padx=5, pady=5)

        self.update_button = ttk.Button(
            button_frame,
            text="Update",
            state="disabled",
            command=self._update_task_pressed,
        )
        self.update_button.pack(side="left", padx=5, pady=5)

        self.delete_button = ttk.Button(
            button_frame,
            text="Delete",
            state="disabled",
            command=self._delete_task_pressed,
        )
        self.delete_button.pack(side="left", padx=5, pady=5)

        self.clear_button = ttk.Button(
            button_frame,
            text="Clear",
            state="normal",
            command=self._clear_tasks_pressed,
        )
        self.clear_button.pack(side="left", padx=5, pady=5)

    @property
    def selected_index(self) -> int:
        return self.__selected_index

    def update_list(self, tasks: List[Task]):
        self.task_tree.delete(*self.task_tree.get_children())
        for i, task in enumerate(tasks):
            self.task_tree.insert(
                "", "end", iid=str(i), values=(task.task, task.status)
            )

    def get_task_from_input(self) -> Task:
        """Gets input field of the task entry and converts it into a Task"""
        return Task(
            task=self.task_entry.get(), status=TaskStatus(self.status_combo.get())
        )

    def show_error(self, title: str, message: str):
        messagebox.showerror(title, message)

    def show_info(self, title: str, message: str):
        messagebox.showinfo(title, message)

    @event
    def on_task_selected(self, e: tk.Event):
        """Event fired when a task is selected in the list"""
        ...

    @on_task_selected.emitter
    def _task_selected(self, e: tk.Event):
        # update selected index
        sel = self.task_tree.selection()
        self.__selected_index = int(sel[0]) if sel else -1

        if len(sel) > 0:
            # populate input fields
            task = self.task_tree.item(sel[0], "values")
            self.task_entry.delete(0, tk.END)
            self.task_entry.insert(0, task[0])
            self.status_combo.set(task[1])

            # enable buttons
            self.update_button.config(state="normal")
            self.delete_button.config(state="normal")

    @event
    def on_add_task_pressed(self):
        """Event fired when user want to add task"""
        ...

    @on_add_task_pressed.emitter
    def _add_task_pressed(self): ...

    @event
    def on_update_task_pressed(self):
        """Event fired when user want to update task"""
        ...

    @on_update_task_pressed.emitter
    def _update_task_pressed(self): ...

    @event
    def on_delete_task_pressed(self):
        """Event fired when user want to delete task"""
        ...

    @on_delete_task_pressed.emitter
    def _delete_task_pressed(self): ...

    @event
    def on_clear_tasks_pressed(self):
        """Event fired when user want to clear tasks"""
        ...

    @on_clear_tasks_pressed.emitter
    def _clear_tasks_pressed(self):
        self.task_tree.selection_remove(self.task_tree.selection())
        self.update_button.config(state="disabled")
        self.delete_button.config(state="disabled")


class TaskPresenter:
    def __init__(self, model: TaskRepository, view: TaskView):
        self.__model = model
        self.__view = view

        # Connect events.
        self.__view.on_add_task_pressed += self.__handle_add_task_pressed
        self.__view.on_update_task_pressed += self.__handle_update_task_pressed
        self.__view.on_delete_task_pressed += self.__handle_delete_task_pressed
        self.__view.on_clear_tasks_pressed += self.__handle_clear_tasks_pressed

        # Display initial tasks
        self.update()

    def update(self):
        self.__view.update_list(self.__model.get_all())

    def __handle_add_task_pressed(self):
        task = self.__view.get_task_from_input()
        if not task.task.strip():
            self.__view.show_error("Error", "Task cannot be empty")
            return
        self.__model.create(task)
        self.update()

    def __handle_update_task_pressed(self):
        task = self.__view.get_task_from_input()

        if not task.task.strip():
            self.__view.show_error("Error", "Task cannot be empty")
        elif (
            self.__view.selected_index < 0
            or self.__view.selected_index >= self.__model.read_task_count()
        ):
            self.__view.show_error("Error", "No task selected")
            return

        self.__model.update(self.__view.selected_index, task)
        self.update()

    def __handle_delete_task_pressed(self):

        if (
            self.__view.selected_index < 0
            or self.__view.selected_index >= self.__model.read_task_count()
        ):
            self.__view.show_error("Error", "No task selected")
            return

        self.__model.delete(self.__view.selected_index)
        self.update()

    def __handle_clear_tasks_pressed(self):
        self.__model.clear()
        self.update()


if __name__ == "__main__":
    import sqlite3

    conn = sqlite3.connect(":memory:")

    table_name = "todo_items"

    conn.execute(
        f"CREATE TABLE {table_name} (task TEXT NOT NULL, status TEXT NOT NULL)"
    )

    repo = TaskRepository(conn=conn, table=table_name)

    sample_tasks = [
        Task(task="Complete project documentation", status=TaskStatus.IN_PROGRESS),
        Task(task="Review code changes"),
        Task(task="Deploy to production"),
    ]

    for item in sample_tasks:
        repo.create(item)

    for item in repo.get_all():
        print(item)

    root = tk.Tk()
    root.title("Task View Component")
    root.geometry("600x400")

    view = TaskView(root)

    presenter = TaskPresenter(repo, view)

    root.mainloop()
