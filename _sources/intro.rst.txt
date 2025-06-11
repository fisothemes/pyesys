Introduction
============

**PyESys** is a Python-native event system that provides thread-safe, type-safe event handling with first-class async support. Designed for real-world applications requiring robust concurrency, simulation, or external control mechanisms.

**Basic Example**:

.. code-block:: python

    from pyesys import create_event

    # Define event signature
    event, listener = create_event(example=lambda msg: None)

    # Define handler
    def log_message(msg: str):
        print(f"Message received: {msg}")

    # Subscribe handler
    listener += log_message

    # Emit event
    event.emit("Hello PyESys!")
    # Output: Message received: Hello PyESys!

**Decorator Example**:

.. code-block:: python

    from pyesys.prop import event
    class Button:
        @event
        def on_click(self):
            """Click event signature"""
        
        @on_click.emitter
        def click(self):
            """Automatically emits after execution"""
            print("Button pressed!")

    def handle_click():
        print("Action performed!")

    btn = Button()
    btn.on_click += handle_click
    btn.click()
    # Output: 
    #   Button pressed!
    #   Action performed!

----

Why PyESys?
-----------

While Python has several event handling solutions, many common approaches present challenges for modern applications:

**Event Bus Patterns**: Many libraries use global event buses with string-based keys, which can create tight coupling and make per-instance event management complex. When each object instance needs its own events, you often need to manage ID strings or implement filtering logic, leading to unnecessary event triggers across unrelated instances.

**Memory Management**: Event systems with bound methods can suffer from memory leaks if not carefully designed with weak references and proper cleanup mechanisms.

**Async/Sync Integration**: Mixing synchronous and asynchronous event handlers consistently can be challenging, especially when you need both to coexist seamlessly.

**Pythonic Design**: Many event systems don't leverage familiar Python patterns, making them feel foreign compared to built-in language features like property descriptors.

PyESys addresses these architectural challenges with a clean, intuitive API:

> *"When controlling real-time systems, I needed clean event handling that works seamlessly across threads and async contexts while feeling natural to Python developers."*

----

Design Approach
---------------

PyESys draws inspiration from familiar Python patterns:

- **Property-like syntax**: The `@event` decorator mirrors Python's `@property` descriptor pattern, making it instantly familiar
- **Operator overloading**: Uses `+=` (subscribe) and `-=` (unsubscribe) following Python's established conventions
- **Per-instance events**: Each object gets its own event instances, eliminating global state and cross-instance interference
- **Type safety**: Runtime signature validation through example functions
- **Memory conscious**: Built-in weak reference handling prevents common memory leak patterns

----

Goals
-----

- **Intuitive syntax** leveraging familiar Python patterns
- **True per-instance events** without global registries or string-based dispatch
- **Seamless sync/async interoperability**
- **Automatic memory management** for bound methods
- **Zero dependencies** with pure Python implementation
- **Runtime signature validation** for type safety
- **Thread-safe by design**

----

Key Use Cases
-------------

1. **Real-time systems**  
   React to sensor inputs/control signals
2. **Simulation frameworks**  
   Decouple models from visualization/control
3. **Plugin architectures**  
   Extend core functionality safely
4. **UI/backend integration**  
   Bridge synchronous and asynchronous worlds
5. **Testable systems**  
   Replace complex callbacks with observable events

----

Design Philosophy
-----------------

- **Explicit over implicit**  
  Handler signatures enforced via example functions
- **Pythonic first**  
  Leverages familiar language patterns like descriptors and operator overloading
- **Concurrency-ready**  
  Thread-safe emission with async support
- **Resource-conscious**  
  Weak references prevent memory leaks
- **Composable**  
  Events work standalone or in complex systems