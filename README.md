# Python Event System (PyESys)

[![Test](https://github.com/fisothemes/pyesys/actions/workflows/test.yaml/badge.svg)](https://github.com/fisothemes/pyesys/actions/workflows/test.yaml)
[![Python version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/pypi/v/pyesys.svg)](https://pypi.org/project/pyesys/)
[![Downloads](https://img.shields.io/pypi/dd/pyesys)](https://pypistats.org/packages/pyesys)
[![Licence](https://img.shields.io/badge/licence-MIT-blue.svg)](LICENSE)

**A Python-native event system with thread-safe, type-safe event handling and first-class async support.**

PyESys brings clean, per-instance event handling to Python using familiar patterns like property descriptors and operator overloading. Perfect for real-time systems, simulations, and any application requiring robust event-driven architecture.

```python
from pyesys import event

class Button:
    @event
    def on_click(self):
        """Click event signature"""
    
    @on_click.emitter
    def click(self):
        print("Button clicked!")

# Each instance gets its own events
btn = Button()
btn.on_click += lambda: print("Handler executed!")
btn.click()
# Output: Button clicked!
#         Handler executed!
```

## Why PyESys?

While Python has several event handling solutions, many common approaches present challenges for modern applications:

**Event Bus Patterns**: Many libraries use global event buses with string-based keys, which can create tight coupling and make per-instance event management complex. When each object instance needs its own events, you often need to manage ID strings or implement filtering logic.

**Memory Management**: Event systems with bound methods can suffer from memory leaks if not carefully designed with weak references and proper cleanup mechanisms.

**Async/Sync Integration**: Mixing synchronous and asynchronous event handlers consistently can be challenging, especially when you need both to coexist seamlessly.

PyESys addresses these architectural challenges with a clean, intuitive API:

- **Per-Instance Events**: No global registries or string-based keys. Each object manages its own events independently.
- **Type Safety**: Runtime signature validation catches handler mismatches early.
- **Async-Ready**: Mix sync and async handlers seamlessly with automatic thread pool handling.
- **Pythonic**: Familiar `@event` decorator syntax inspired by `@property`, plus `+=`/`-=` operators.
- **Memory Safe**: Built-in weak references prevent common memory leak patterns.
- **Thread Safe**: Safe concurrent event emission across multiple threads.

## Quick Start

### Installation

```bash
pip install pyesys
```

Requires Python 3.12+. Zero dependencies.

### Basic Usage

```python
from pyesys import create_event

# Create event with signature validation
event, listener = create_event(example=lambda msg: None)

def log_message(msg: str):
    print(f"[LOG] {msg}")

# Subscribe and emit
listener += log_message
event.emit("Hello PyESys!")
# Output: [LOG] Hello PyESys!
```

### Class-Based Events

```python
from pyesys import event

class FileProcessor:
    @event
    def on_progress(self, filename: str, percent: float):
        """Progress update event"""
    
    @on_progress.emitter
    def _update_progress(self, filename: str, percent: float):
        pass  # Event automatically emitted
    
    def process(self, filename: str):
        for i in range(0, 101, 25):
            self._update_progress(filename, i)

# Each processor has independent events
processor = FileProcessor()
processor.on_progress += lambda f, p: print(f"{f}: {p}% complete")

processor.process("data.txt")
# Output: data.txt: 0% complete
#         data.txt: 25% complete
#         ...
```

## Advanced Features

### Event Chaining

Create processing pipelines by chaining events between objects:

```python
class DataProcessor:
    @event
    def on_processed(self, data: dict):
        pass
    
    @on_processed.emitter
    def process(self, data: dict):
        # Transform data
        return {"processed": True, **data}

class DataValidator:
    def validate(self, data: dict):
        print(f"Validating: {data}")

processor = DataProcessor()
validator = DataValidator()

# Chain processors
processor.on_processed += validator.validate
processor.process({"id": 123})
```

### Async Support

Mix synchronous and asynchronous handlers effortlessly:

```python
import asyncio

async def async_handler(data):
    await asyncio.sleep(0.1)
    print(f"Async: {data}")

def sync_handler(data):
    print(f"Sync: {data}")

listener += [sync_handler, async_handler]
await event.emit_async("mixed-handlers")
# Both handlers run concurrently
```

### Bulk Operations

Efficiently manage multiple handlers:

```python
# Bulk subscribe
listener += [handler1, handler2, handler3]

# Bulk unsubscribe  
listener -= {handler1, handler2}

# Introspection
print(f"Active handlers: {listener.handler_count()}")
```

### Production Error Handling

```python
def error_handler(exception, handler_func):
    logger.error(f"Handler {handler_func.__name__} failed: {exception}")

event, listener = create_event(
    example=lambda x: None,
    error_handler=error_handler
)
# Failing handlers won't crash the system
```

## Real-World Use Cases

- **Real-time Systems**: React to sensor inputs and control signals
- **Simulation Frameworks**: Decouple models from visualization/control  
- **Plugin Architectures**: Extend applications safely with event hooks
- **UI/Backend Integration**: Bridge sync and async worlds seamlessly
- **Testable Systems**: Replace complex callbacks with observable events

## API Overview

### Core Functions

#### `create_event(example, *, allow_duplicates=True, error_handler=None)`

Creates an event emitter and listener pair with signature validation:

```python
from pyesys import create_event

event, listener = create_event(
    example=lambda x, y: None,  # Handler signature template
    allow_duplicates=False,     # Prevent duplicate subscriptions
    error_handler=custom_handler  # Handle exceptions gracefully
)
```

#### `@event` Decorator

Creates class-level or module-level events using familiar decorator syntax:

```python
from pyesys import event

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

### Event Class

The `Event` class provides the core event management functionality:

**Subscription Management:**
- `event += handler` - Subscribe directly to event
- `event -= handler` - Unsubscribe directly from event
- `listener += handler` - Subscribe via listener interface
- `listener -= handler` - Unsubscribe via listener interface
- `event += [h1, h2, h3]` - Bulk subscribe
- `event.clear()` - Remove all handlers

**Event Emission:**
- `event.emit(*args, **kwargs)` - Synchronous emission
- `await event.emit_async(*args, **kwargs)` - Asynchronous emission

**Introspection:**
- `event.handler_count()` - Number of active handlers
- `event.handlers` - List of current handlers
- `bool(event)` - True if handlers exist
- `len(event)` - Same as handler_count()

### Key Features

**Type Safety**: Runtime signature validation through example functions ensures handlers match expected signatures, catching errors early.

**Memory Management**: Automatic weak reference handling for bound methods prevents memory leaks without requiring manual cleanup.

**Thread Safety**: All operations are thread-safe, allowing safe concurrent access from multiple threads.

**Async Integration**: Seamlessly mix sync and async handlers. Async handlers run concurrently, sync handlers run in thread pools during async emission.

**Error Resilience**: Custom error handlers prevent one failing handler from affecting others, crucial for production systems.

## Alternative Usage Patterns

### Direct Event Instantiation

For more control, instantiate events directly:

```python
from pyesys.event import Event

def example_sig(a: int, b: str) -> None:
    pass

msg_event = Event(example=example_sig)

def on_message(a: int, b: str) -> None:
    print(f"Got {a} and {b}")

# Subscribe directly to the event
msg_event += on_message
msg_event.emit(1, "hello")

# Or use the listener interface
msg_event.listener += on_message
```

### Module-Level Events

Create application-wide events at module level:

```python
from pyesys import event

@event
def on_user_login(user_id: str, timestamp: float) -> None:
    """Fired when a user successfully logs in"""

@on_user_login.emitter
def login_user(user_id: str, timestamp: float) -> None:
    """Authenticate user and emit login event"""
    print(f"User {user_id} authenticated at {timestamp}")

# Subscribe to login events
def update_last_seen(user_id: str, timestamp: float):
    print(f"Updating last seen for {user_id}")

on_user_login += update_last_seen
```

## Testing

PyESys uses **pytest** and **pytest-asyncio**. To install dev dependencies and run the test suite:

```bash
pip install -e .[dev]
pytest -q
```

Test files live under `tests/`:

- `tests/unit/test_handler.py` – tests for `EventHandler`
- `tests/unit/test_event.py` – tests for `Event` (sync & async)
- `tests/unit/test_prop.py` – tests for the `@event` decorator
- `tests/integration/test_pyesys_end_to_end.py` – end-to-end integration tests

All tests must pass before merging any changes.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for details on:

- Setting up a development environment
- Branching and workflow conventions
- Coding style & formatting (PEP 8, Black, type hints)
- Writing tests and running them
- Submitting pull requests

## Documentation

- **📖 [Full Documentation](https://fisothemes.github.io/pyesys/)**
- **🐛 [Issue Tracker](https://github.com/fisothemes/pyesys/issues)**
- **📋 [Examples](./examples/)**

---

*PyESys - Pythonic events for modern applications* 🐍✨