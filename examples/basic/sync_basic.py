from pyesys import create_event

event, listener = create_event(example=lambda x, y: None)

def handler(x, y):
    print(f"Received: {x} and {y}")

listener += handler

event.emit("hello", 42)

