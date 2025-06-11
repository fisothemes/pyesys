# Python Event System (PyESys)

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

## Documentation

- **📖 [Full Documentation](https://fisothemes.github.io/pyesys/)**
- **💻 [Source Code](https://github.com/fisothemes/pyesys)**
- **🐛 [Issue Tracker](https://github.com/fisothemes/pyesys/issues)**
- **📋 [Examples](https://github.com/fisothemes/pyesys/tree/master/examples)**

## License

MIT License - see [LICENSE](https://github.com/fisothemes/pyesys/blob/master/LICENSE) file.

---

*PyESys - Pythonic events for modern applications* 🐍✨