import tkinter as tk
from pyesys import create_event


class CounterModel:
    """
    The Model manages the application state and business logic.
    It exposes only the operations and state needed by the presenter.
    """
    def __init__(self, initial_count: int = 0):
        self.__count: int = initial_count

    def increment(self):
        self.__count += 1

    def decrement(self):
        self.__count -= 1

    @property
    def count(self) -> int:
        return self.__count

class CounterView:
    """
    The View manages the UI and exposes events for user actions.
    It knows nothing about business logic or data storage.
    All interactions happen via events and update methods.
    """
    def __init__(self, root: tk.Tk):
        # Window setup
        self.root = root
        self.root.title("PyESys Counter")
        self.root.geometry("300x140")

        # Display label for the counter value
        self.__label = tk.Label(self.root, text="Count: 0", font=("Arial", 24))
        self.__label.pack(pady=20)

        # Button frame for clean button alignment
        button_frame = tk.Frame(self.root)
        button_frame.pack()

        # --- Events: Use PyESys create_event for type-safe, thread-safe event handling

        # Increment event and its listener interface
        self.__increment_event, self.on_increment_pressed = create_event(example=lambda: None)
        self.__increment_button = tk.Button(
            button_frame, text="Increment", font=("Arial", 16), command=self.__increment_event.emit
        )
        self.__increment_button.pack(side=tk.LEFT, padx=5)

        # Decrement event and its listener interface
        self.__decrement_event, self.on_decrement_pressed = create_event(example=lambda: None)
        self.__decrement_button = tk.Button(
            button_frame, text="Decrement", font=("Arial", 16), command=self.__decrement_event.emit
        )
        self.__decrement_button.pack(side=tk.RIGHT, padx=5)

    def update(self, count: int):
        """
        Update the counter display.
        Called by the presenter whenever the model changes.
        """
        self.__label.config(text=f"Count: {count}")


class CounterPresenter:
    """
    The Presenter wires the Model and View together.
    It subscribes to view events, updates the model, and ensures the view always
    reflects the model state. All UI logic and business logic remain decoupled.
    """
    def __init__(self, model: CounterModel, view: CounterView):
        self.__model = model
        self.__view = view

        # Subscribe model and view update handlers to view events
        # The order guarantees the model updates before the view refreshes.
        self.__view.on_increment_pressed += self.__model.increment   # Update model
        self.__view.on_increment_pressed += self.__handle_change     # Refresh view

        self.__view.on_decrement_pressed += self.__model.decrement   # Update model
        self.__view.on_decrement_pressed += self.__handle_change     # Refresh view

        # Ensure view displays correct initial state
        self.__handle_change()

    def __handle_change(self):
        """Synchronize the view with the current model state."""
        self.__view.update(self.__model.count)


if __name__ == "__main__":
    # Create application components
    root = tk.Tk()
    model = CounterModel()
    view = CounterView(root)
    presenter = CounterPresenter(model, view)
    # Start Tkinter main loop
    root.mainloop()
