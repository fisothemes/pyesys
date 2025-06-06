from pyesys import create_event

event_a, on_a = create_event(example=lambda msg: None)
event_b, on_b = create_event(example=lambda msg: None)

def handler_a(msg):
    print(f"Handler A received: {msg}")
    event_b.emit(f"{msg} -> from A")

def handler_b(msg):
    print(f"Handler B received: {msg}")

on_a += handler_a
on_b += handler_b

# Trigger the first
event_a.emit("Hello")
