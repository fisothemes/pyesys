from pyesys import event

@event
def on_hello(name: str) -> None: ...

@on_hello.emitter
def hello(name: str) -> None:
    print(f"Saying hello to {name}...")

def handler(name: str) -> None:
    print(f"Received hello event for {name}.")

on_hello += handler

hello("World")