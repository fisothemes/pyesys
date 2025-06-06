# Python Event System (PyESys)

[![Test](https://github.com/fisothemes/pyesys/actions/workflows/test.yaml/badge.svg)](https://github.com/fisothemes/pyesys/actions/workflows/test.yaml)
[![Python version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/pypi/v/pyesys.svg)](https://pypi.org/project/pyesys/)
[![Downloads](https://img.shields.io/pypi/dd/pyesys)](https://pypi.org/project/pyesys/)
[![Licence](https://img.shields.io/badge/licence-MIT-blue.svg)](LICENSE)

**A thread-safe, type-safe Python Event SYStem with async support.**

PyESys provides a lightweight, dependency-free event/pub-sub framework. It supports:

* **Synchronous and asynchronous** handlers
* **Thread-safe** subscribe/unsubscribe/emit
* **Weak-reference clean-up** of bound-method handlers
* **Runtime signature checking** (handler arity must match an example signature)
* **Custom error handling** per handler
* **Duplicate-subscription control**
* **Introspection** (`handler_count`, `handlers`)
* **Class-level and module-level events** with decorator syntax


## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)

   * [Creating an Event with `create_event`](#creating-an-event-with-create_event)
   * [Creating an Event Directly with `Event.new` or `Event`](#creating-an-event-directly-with-eventnew-or-event)
   * [Subscribing & Emitting (Sync)](#subscribing--emitting-sync)
   * [Subscribing & Emitting (Async)](#subscribing--emitting-async)
   * [Subscribing Multiple Handlers at Once](#subscribing-multiple-handlers-at-once)
   * [Class-Level & Module-Level Events with `@event`](#class-level--module-level-events-with-event)
3. [API Overview](#api-overview)

   * [`EventHandler`](#eventhandler)
   * [`Event`](#event)
   * [`create_event`](#create_event)
   * [`@event` Decorator](#event-decorator)
4. [Testing](#testing)
5. [Contributing](#contributing)
6. [Licence](#licence)


## Installation

Requires **Python 3.12+**.

Install from PyPI:

```bash
pip install pyesys
```

Or install in editable (development) mode:

```bash
git clone https://github.com/fisothemes/pyesys.git
cd pyesys
pip install -e .[dev]
```

> The `[dev]` extra installs development-only dependencies (e.g., `pytest`, `pytest-asyncio`, `black`, `sphinx`).


## Quick Start

### Creating an Event with `create_event`

Each event is defined by an “example” function whose signature specifies the required arguments. Use `create_event(...)` (or `Event.new(...)`) to create a new event:

```python
from pyesys.event import create_event

# Example function signature: (int, str) -> None
event_obj, listener = create_event(example=lambda x, y: None)
```

* `event_obj` is the dispatcher (an instance of `Event`).
* `listener` is an `Event.Listener` interface—use `listener += handler` to subscribe and `listener -= handler` to unsubscribe.

If you prefer a named function:

```python
def example_sig(a: int, b: str) -> None:
    pass

event_obj, listener = create_event(example=example_sig)
```

### Creating an Event Directly with `Event.new` or `Event`

You may also instantiate an `Event` directly, which offers the same functionality. For instance:

```python
from pyesys.event import Event

def example_sig(a: int, b: str) -> None:
    pass

# Using Event.new() (alias for create_event):
event_obj, listener = Event.new(example=example_sig)

# Equivalent direct instantiation:
msg_event = Event(example=example_sig)

# Create a handler:
def on_message(a: int, b: str) -> None:
    print(f"Got {a} and {b}")

# Subscribe a handler:
msg_event.listener += on_message

# Emit:
msg_event.emit(1, "hello")
# prints: Got 1 and hello
```

Here, `msg_event.Listener` is used to manage subscriptions, and `msg_event.emit(...)` dispatches to all subscribed handlers.


### Subscribing & Emitting (Sync)

Handlers must accept the same parameters as the example and return `None`:

```python
def on_data(x: int, name: str) -> None:
    print(f"Received: {x}, {name}")

# Subscribe with +=
listener += on_data

# Emit synchronously (blocks until all handlers finish)
event_obj.emit(42, "hello")  
# prints: Received: 42, hello

# Unsubscribe with -=
listener -= on_data
```

**Duplicate-subscription control**
By default, `allow_duplicates=True`, so adding the same handler twice invokes it twice on each `emit`. To prevent duplicates:

```python
event_obj, listener = create_event(example=lambda x: None, allow_duplicates=False)
```


### Subscribing & Emitting (Async)

Call `emit_async(...)` to dispatch all handlers concurrently:

1. **`async def` handlers** are awaited directly.
2. **Sync handlers** run in a thread pool.

```python
import asyncio
from pyesys.event import create_event

# Example signature: (int,) -> None
event_obj, listener = create_event(example=lambda x: None)

async def async_handler(v: int) -> None:
    await asyncio.sleep(0.1)
    print(f"Async got: {v}")

def sync_handler(v: int) -> None:
    print(f"Sync got: {v}")

listener += async_handler
listener += sync_handler

async def main():
    await event_obj.emit_async(10)
    # prints in some order:
    #   Sync got: 10
    #   Async got: 10

asyncio.run(main())
```

If there are no handlers, `emit_async(...)` returns immediately without error.


# Subscribing Multiple Handlers at Once

You can subscribe multiple handlers at once using a `list`, `tuple`, or `set`:

```python
listener += [handler1, handler2, handler3]
listener += (handler4, handler5)
listener += {handler6, handler7, handler8} # Order is not guaranteed for sets
```

To unsubscribe multiple handlers in one step, use the same container type:

```python
listener -= [handler1, handler2, handler3]
listener -= (handler4, handler5)
listener -= {handler6, handler7, handler8}
```


### Class-Level & Module-Level Events with `@event`

PyESys includes an `@event` decorator (in `pyesys.prop`) for defining events on classes or at module level. Each instance or module gets its own event, managed automatically:

#### Class-level events

```python
from pyesys.prop import event

# Class-level event (per-instance)
class Button:
    @event
    def on_click(self):
        """Event signature definition (no parameters besides self)."""
        pass

    @on_click.emitter
    def click(self):
        """This method is an emitter—after running, it fires `on_click`."""
        print(f"Button {id(self)} was clicked!")

class Counter:
    def __init__(self):
        self.count = 0

    def increment(self):
        """Signature matches `on_click` (no extra args)."""
        self.count += 1
        print(f"Count = {self.count}")

# Usage
counter = Counter()
button = Button()

# Subscribe the counter’s `increment` method to the button’s `on_click` event
button.on_click += counter.increment

# Trigger the emitter
button.click()
# prints: Button 140280689482800 was clicked!
# prints: Count = 1
```

#### Module-level events

```python
# Module-level event (global)
from pyesys.prop import event

@event
def on_global_event(message: str):
    """Global event signature: handlers must accept a single str."""
    pass

@on_global_event.emitter
def trigger_global(message: str):
    """This function triggers the module-level event after running."""
    print(f"Global: {message}")

# Usage

def global_handler(msg: str) -> None:
    print(f"Handled globally: {msg}")

on_global_event += global_handler
trigger_global("Hello, world!")
# prints: Global: Hello, world!
# prints: Handled globally: Hello, world!
```

**Key features of `@event`:**

* **Automatic signature detection**: Event signature is derived from the decorated function/method.
* **Per-instance vs global**: Class methods create per-instance events; module functions create a single global event.
* **Emitter decorator**: Use `@event_name.emitter` to define methods/functions that automatically fire the event after their body.
* **Mixed sync/async support**: Both synchronous and asynchronous handlers are supported seamlessly.
* **Thread safety**: Async handlers are dispatched in a background thread when emitted from a sync context.


## API Overview

### `EventHandler`

Located in `pyesys.handler`. Wraps a callable handler to:

* Detect bound methods vs. free functions
* Store a **weak reference** to the instance (for bound methods)
* Provide `is_alive()` to check if the instance is still alive
* Implement `__eq__` / `__hash__` so duplicate detection works correctly
* Expose `get_callback()` to reconstruct a live callable

Most users will **not** instantiate `EventHandler` directly; it’s used internally by `Event`.


### `Event`

Located in `pyesys.event`. Core class that manages subscriptions and dispatch:

```python
class Event:
    def __init__(
        self,
        *,
        allow_duplicates: bool = True,
        error_handler: Optional[ErrorHandler] = None
    ):
        ...
```

* **Constructor arguments**:

  * `allow_duplicates`: If `False`, the same handler won’t be added twice.
  * `error_handler`: A callable `(exception, handler)` used when any handler raises.

#### Core methods & properties

* `Listener` (an `Event.Listener`):

  * Subscribe with `Listener += handler`
  * Unsubscribe with `Listener -= handler`
  * Query with `Listener.handler_count()`

* `emit(*args, **kwargs)`

  * Synchronously invoke all live handlers under a lock.
  * Exceptions in each handler are routed to `error_handler` without stopping other handlers.
  * Async handlers (coroutines) returned in sync emit are silently closed (ignored).

* `async emit_async(*args, **kwargs)`

  * Dispatch all handlers concurrently:

    1. **`async def` handlers** are awaited.
    2. **Sync handlers** run via `loop.run_in_executor`.
  * All exceptions are caught and passed to `error_handler`.

* `clear()`

  * Remove all handlers (dropping subscriptions).

* `handler_count()` (method)

  * Returns the number of currently alive handlers, pruning any dead bound methods.

* `handlers` (property)

  * Returns a **list** of live callables (reconstructed via `EventHandler.get_callback()`).
  * Mutating this returned list does **not** affect the internal state.

* `__bool__()` / `__len__()`

  * Boolean truth is `True` if there is at least one live handler.
  * `len(event_obj)` returns `handler_count()`.

* `new(example, *, allow_duplicates, error_handler) → (Event, Event.Listener)`

  * Factory method (alias: `create_event`).
  * Example usage:

    ```python
    event_obj, listener = Event.new(
        example = lambda x, y: None,
        allow_duplicates = False,
        error_handler = custom_handler
    )
    ```


### `create_event`

A convenience alias for `Event.new(...)`. Import from:

```python
from pyesys.event import create_event

event_obj, listener = create_event(
    example = lambda a, b: None,
    allow_duplicates = True
)
```


### `@event` Decorator

Located in `pyesys.prop`. Creates class-level or module-level events using decorator syntax:

```python
from pyesys.prop import event

# Class-level event (per-instance)
class MyClass:
    @event
    def on_something(self, value: int):
        """Event signature: handlers must accept a single int."""
        pass

    @on_something.emitter
    def do_something(self, value: int):
        """This method triggers the on_something event after running."""
        print(f"Doing something with {value}")

# Module-level event (global)
@event
def on_global_event(message: str):
    """Global event signature: handlers must accept a single str."""
    pass

@on_global_event.emitter
def trigger_global(message: str):
    """This function triggers the module-level event after running."""
    print(f"Global: {message}")
```

* **Automatic signature detection**: Event signature is derived from the decorated function/method.
* **Per-instance vs global**: Class methods create per-instance events; module functions create a single global event.
* **Emitter decorator**: Use `@event_name.emitter` to define methods/functions that automatically fire the event after their body.
* **Mixed sync/async support**: Both synchronous and asynchronous handlers are supported seamlessly.
* **Thread safety**: Async handlers are dispatched in a background thread when emitted from a sync context.


## Testing

PyESys uses **pytest** and **pytest-asyncio**. To install dev dependencies and run the test suite:

```bash
pip install -e .[dev]
pytest -q
```

Test files live under `tests/`:

* `tests/unit/test_handler.py` – tests for `EventHandler`
* `tests/unit/test_event.py` – tests for `Event` (sync & async)
* `tests/unit/test_prop.py` – tests for the `@event` decorator
* `tests/integration/test_pyesys_end_to_end.py` – end-to-end integration tests

All tests must pass before merging any changes.


## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for details on:

* Setting up a development environment
* Branching and workflow conventions
* Coding style & formatting (PEP 8, Black, type hints)
* Writing tests and running them
* Submitting pull requests


## Licence

This project is licenced under the **MIT Licence**. See [LICENSE](LICENSE) for details.

© 2025 Goodwill Mzumala
