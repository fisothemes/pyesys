from pyesys import event

@event
def on_click() -> None: ...

@on_click.emitter
def click() -> None:
    print("Beginning click...")

def open_window() -> None:
    print("Opening window...")

def loading_file() -> None:
    print("Loading file...")

on_click += open_window
on_click += loading_file

click()