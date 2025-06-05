from pyesys import create_event

def custom_error_handler(exception: Exception, handler) -> None:
    print(
        f"[Custom Error Handler] Handler {handler.__name__ if handler else '<invalid handler>'} " +
        f"raised exception: {exception}")

event, listener = create_event(example=lambda x: None, error_handler=custom_error_handler)

def bad(x):
    raise ValueError("Ahhhh! Life has no meaning!")

def good(x):
    print(f"Received: {x} the meaning of life.")

listener += bad
listener += good

event.emit(42)