import tkinter as tk
from tkinter import ttk
import sqlite3

from tasks import TaskView, TaskRepository, TaskPresenter
from user_events import UserEventRepository, UserEventView, UserEventPresenter


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("To-Do App")
        self.geometry("800x500")

        # Database setup
        self.conn = sqlite3.connect("todo.db")
        self._init_schema()

        self.task_repo = TaskRepository(self.conn, "todo_items")
        self.event_repo = UserEventRepository(self.conn, "user_events")

        # Layout setup
        self._create_layout()

        # Routing and presenter/view wiring
        self.views = {}
        self.presenters = {}
        self._init_views_and_presenters()

        self.route("tasks")

    def _init_schema(self):
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS todo_items (
                task TEXT NOT NULL,
                status TEXT NOT NULL
            )"""
        )
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS user_events (
                date TEXT NOT NULL,
                description TEXT NOT NULL
            )"""
        )

    def _create_layout(self):
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)

        self.sidebar = ttk.Frame(container, width=150)
        self.sidebar.pack(side="left", fill="y")

        self.content = ttk.Frame(container)
        self.content.pack(side="right", fill="both", expand=True)

        self._add_sidebar_button("Tasks", lambda: self.route("tasks"))
        self._add_sidebar_button("History", lambda: self.route("events"))

    def _add_sidebar_button(self, text: str, command: callable):
        button = ttk.Button(self.sidebar, text=text, command=command)
        button.pack(fill="x", padx=5, pady=5)

    def _init_views_and_presenters(self):
        # Views
        task_view = TaskView(self.content)
        event_view = UserEventView(self.content)

        self.views["tasks"] = task_view
        self.views["events"] = event_view

        for view in self.views.values():
            view.pack_forget()

        # Presenters
        event_presenter = UserEventPresenter(self.event_repo, event_view)
        self.presenters["events"] = event_presenter

        # Logging setup (decoupled via lambdas)
        def log_action(action: str):
            task = task_view.get_task_from_input()
            task_str = f"{task.task}" if task.task.strip() else "<empty>"
            event_presenter.log(f"{action} task: {task_str} | {task.status}")

        task_view.on_add_task_pressed += lambda: log_action("Added")
        task_view.on_update_task_pressed += lambda: log_action("Updated")
        task_view.on_delete_task_pressed += lambda: log_action("Deleted")
        task_view.on_clear_tasks_pressed += lambda: event_presenter.log("Cleared all tasks")

        self.presenters["tasks"] = TaskPresenter(model=self.task_repo, view=task_view)

    def route(self, name: str):
        for view in self.views.values():
            view.pack_forget()
        self.views[name].pack(fill="both", expand=True)


if __name__ == "__main__":
    app = App()
    app.mainloop()
