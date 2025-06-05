from pyesys import create_event

calls = []

def handler(x):
    calls.append(x)
    print(f"Handled: {x}")

event1, listener1 = create_event(example=lambda x: None, allow_duplicates=True)

listener1 += handler
listener1 += handler

event1.emit("A")

event2, listener2 = create_event(example=lambda x: None, allow_duplicates=False)

listener2 += handler
listener2 += handler

event2.emit("B")