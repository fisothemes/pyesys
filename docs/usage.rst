Usage Guide
===========

This guide demonstrates how to leverage PyESys for effective event-driven programming:

- Create and emit events with type safety
- Subscribe synchronous and asynchronous handlers
- Use `@event` decorators for clean API design
- Manage handler lifecycles efficiently
- Chain events for complex workflows
- Handle errors gracefully in production

----

Installation
------------

PyESys requires Python 3.12+ and has zero external dependencies.

.. code-block:: bash

    pip install pyesys

For local development with testing tools:

.. code-block:: bash

    git clone https://github.com/fisothemes/pyesys.git
    cd pyesys
    pip install -e .[dev]

----

Quick Start: Creating Events
----------------------------

The `create_event()` function creates an event emitter and listener pair. Use an example function to define the expected handler signature:

.. code-block:: python

    from pyesys import create_event

    # Create event with signature validation
    event, listener = create_event(example=lambda msg: None)

    def log_message(msg: str):
        print(f"[LOG] {msg}")

    def store_message(msg: str):
        # Store to database, file, etc.
        pass

    # Subscribe handlers
    listener += log_message
    listener += store_message

    # Emit to all subscribers
    event.emit("System started successfully")

The example function enforces that all handlers must accept exactly one parameter. This catches signature mismatches at subscription time, preventing runtime errors.

----

Decorator Pattern: Module-Level Events
--------------------------------------

For application-wide events, use the `@event` decorator at module level to create clean, reusable event APIs:

.. code-block:: python

    from pyesys import event

    @event
    def on_user_login(user_id: str, timestamp: float) -> None:
        """Fired when a user successfully logs in"""

    @on_user_login.emitter
    def login_user(user_id: str, timestamp: float) -> None:
        """Authenticate user and emit login event"""
        # Perform authentication logic here
        print(f"User {user_id} authenticated at {timestamp}")
        # Event automatically emitted after function completes

    # Subscribe to login events
    def update_last_seen(user_id: str, timestamp: float):
        print(f"Updating last seen for {user_id}")

    def log_access(user_id: str, timestamp: float):
        print(f"Access logged: {user_id} at {timestamp}")

    on_user_login += [update_last_seen, log_access]

    # Trigger authentication and event
    import time
    login_user("alice", time.time())


The `@event` decorator creates a module-level event, while `@on_user_login.emitter` creates a function that automatically emits the event after executing its body.

----

Decorator Pattern: Per-Instance Events
--------------------------------------

Class-level events provide per-instance isolation, perfect for component-based architectures:

.. code-block:: python

    from pyesys import event

    class FileProcessor:
        @event
        def on_progress(self, filename: str, percent: float) -> None:
            """Progress update event"""
        
        @event
        def on_complete(self, filename: str, result: dict) -> None:
            """Processing complete event"""
        
        @on_progress.emitter
        def _update_progress(self, filename: str, percent: float):
            """Internal progress updater"""
            pass  # Event emitted automatically
        
        @on_complete.emitter
        def _finish_processing(self, filename: str, result: dict):
            """Internal completion handler"""
            pass  # Event emitted automatically
        
        def process_file(self, filename: str):
            print(f"Starting processing: {filename}")
            
            # Simulate processing with progress updates
            for i in range(0, 101, 25):
                self._update_progress(filename, i)
            
            result = {"status": "success", "lines": 1000}
            self._finish_processing(filename, result)

    # Each processor instance has independent events
    processor1 = FileProcessor()
    processor2 = FileProcessor()

    # Subscribe different handlers to each instance
    processor1.on_progress += lambda f, p: print(f"P1: {f} at {p}%")
    processor2.on_progress += lambda f, p: print(f"P2: {f} at {p}%")

    processor1.process_file("data1.txt")
    processor2.process_file("data2.txt")

Each `FileProcessor` instance maintains its own event handlers, preventing cross-instance interference.

----

Efficient Handler Management
----------------------------

PyESys supports bulk operations for managing multiple handlers efficiently:

.. code-block:: python

    from pyesys import create_event

    event, listener = create_event(example=lambda data: None)

    def handler_a(data): print("A:", data)
    def handler_b(data): print("B:", data) 
    def handler_c(data): print("C:", data)
    def handler_d(data): print("D:", data)

    # Bulk subscribe using collections
    listener += [handler_a, handler_b, handler_c]
    listener += {handler_d}  # Sets work too

    print(f"Active handlers: {listener.handler_count()}")  # 4

    # Bulk unsubscribe
    listener -= [handler_a, handler_c]
    print(f"Remaining handlers: {listener.handler_count()}")  # 2

    # Clear all handlers
    event.clear()
    print(f"After clear: {listener.handler_count()}")  # 0

This pattern is especially useful for plugin systems or dynamic handler registration scenarios.

----

Event Chaining and Workflows
----------------------------

Chain events between objects to create flexible processing pipelines:

.. code-block:: python

    from pyesys import event
    from abc import ABC
    import json

    class DataProcessor(ABC):
        @event
        def on_processed(self, data: dict, metadata: dict) -> None:
            """Emitted when processing completes"""
        
        @on_processed.emitter
        def _emit_processed(self, data: dict, metadata: dict):
            """Internal method to emit processing event"""
            pass

    class JsonParser(DataProcessor):
        def process(self, raw_data: str):
            print("Parsing JSON...")
            try:
                data = json.loads(raw_data)
                metadata = {"parser": "json", "status": "success"}
            except json.JSONDecodeError:
                data = {}
                metadata = {"parser": "json", "status": "error"}
            
            self._emit_processed(data, metadata)

    class DataValidator(DataProcessor):
        def validate(self, data: dict, metadata: dict):
            print(f"Validating data (previous: {metadata['status']})...")
            
            if metadata["status"] == "error":
                metadata["validator"] = "skipped"
            else:
                # Perform validation
                is_valid = "name" in data and "id" in data
                metadata["validator"] = "passed" if is_valid else "failed"
            
            self._emit_processed(data, metadata)

    class DataStore(DataProcessor):
        def store(self, data: dict, metadata: dict):
            print(f"Storing data (validation: {metadata.get('validator', 'none')})...")
            
            if metadata.get("validator") == "passed":
                print(f"✓ Stored: {data}")
                metadata["storage"] = "success"
            else:
                print("✗ Storage skipped due to validation failure")
                metadata["storage"] = "skipped"
            
            self._emit_processed(data, metadata)

    # Create pipeline
    parser = JsonParser()
    validator = DataValidator()
    store = DataStore()

    # Chain the processors
    parser.on_processed += validator.validate
    validator.on_processed += store.store

    # Final result handler
    def log_final_result(data: dict, metadata: dict):
        print(f"Pipeline complete: {metadata}")

    store.on_processed += log_final_result

    # Process data through the pipeline
    parser.process('{"name": "Alice", "id": 123}')
    print("---")
    parser.process('{"invalid": json}')

This pattern enables flexible, testable processing chains where each component can be developed and tested independently.

----

Asynchronous Event Handling
---------------------------

PyESys seamlessly handles mixed sync/async handlers, running them concurrently when possible:

.. code-block:: python

    import asyncio
    import time
    from pyesys import create_event

    event, listener = create_event(example=lambda data: None)

    def sync_handler(data):
        """Synchronous handler - runs in thread pool"""
        print(f"Sync processing: {data}")
        time.sleep(0.1)  # Simulate work
        print(f"Sync complete: {data}")

    async def async_handler(data):
        """Asynchronous handler - runs in event loop"""  
        print(f"Async processing: {data}")
        await asyncio.sleep(0.1)  # Simulate async work
        print(f"Async complete: {data}")

    async def slow_async_handler(data):
        """Another async handler with different timing"""
        await asyncio.sleep(0.2)
        print(f"Slow async complete: {data}")

    # Subscribe mixed handler types
    listener += [sync_handler, async_handler, slow_async_handler]

    async def main():
        print("Emitting to mixed handlers...")
        await event.emit_async("test-data")
        print("All handlers completed")

    # Run the async event
    asyncio.run(main())

The `emit_async()` method ensures all handlers complete before returning, with sync handlers running in a thread pool to avoid blocking the event loop.

----

Production Error Handling
-------------------------

Implement robust error handling to prevent one failing handler from affecting others:

.. code-block:: python

    from pyesys import create_event
    import logging

    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    def production_error_handler(exception: Exception, handler_func):
        """Custom error handler for production use"""
        logger.error(
            f"Event handler {handler_func.__name__} failed: {exception}",
            exc_info=True
        )
        
        # Could also:
        # - Send to error tracking service
        # - Increment failure metrics
        # - Disable repeatedly failing handlers

    # Create event with custom error handling
    event, listener = create_event(
        example=lambda x: None,
        error_handler=production_error_handler
    )

    def reliable_handler(x):
        print(f"Reliable handler: {x}")

    def unreliable_handler(x):
        if x == "trigger_error":
            raise ValueError("Something went wrong!")
        print(f"Unreliable handler: {x}")

    def another_handler(x):
        print(f"Another handler: {x}")

    listener += [reliable_handler, unreliable_handler, another_handler]

    # Test error handling
    event.emit("normal_data")      # All handlers run
    print("---")
    event.emit("trigger_error")    # unreliable_handler fails, others continue

Custom error handlers allow you to integrate with your monitoring and logging infrastructure while ensuring system resilience.

----

Debugging and Introspection
---------------------------

PyESys provides tools for debugging and monitoring event handler state:

.. code-block:: python

    from pyesys import create_event

    event, listener = create_event(example=lambda x: None)

    def handler_one(x): pass
    def handler_two(x): pass

    listener += [handler_one, handler_two]

    # Inspect current handlers
    print(f"Handler count: {listener.handler_count()}")

    print("\nActive handlers:")
    for i, handler in enumerate(event.handlers):
        print(f"  {i}: {handler}")

    # Check if specific handler is subscribed
    is_subscribed = any(h == handler_one for h in event.handlers)
    print(f"\nhandler_one subscribed: {is_subscribed}")

    # Remove specific handler
    listener -= handler_one
    print(f"After removal: {listener.handler_count()}")

These introspection capabilities are valuable for debugging complex event-driven systems and ensuring proper handler lifecycle management.

----

Best Practices
--------------

**Type Safety**: Always use descriptive example functions that match your handler signatures:

.. code-block:: python

    # Good: Clear signature
    event, listener = create_event(
        example=lambda user_id: str, action: str, timestamp: float: None
    )

    # Avoid: Vague signatures  
    event, listener = create_event(example=lambda *args: None)

**Memory Management**: PyESys uses weak references automatically, but be mindful of handler lifecycles:

.. code-block:: python

    class EventHandler:
        def handle_event(self, data):
            print(f"Handling: {data}")

    # Handler will be garbage collected when 'handler' goes out of scope
    handler = EventHandler()
    listener += handler.handle_event

    # Keep reference if handler needs to persist
    self.persistent_handler = EventHandler()
    listener += self.persistent_handler.handle_event

**Error Resilience**: Always implement custom error handlers in production systems to prevent cascading failures.

----

More Examples
-------------

Find complete working examples and advanced patterns in the GitHub repository: 
    
    - https://github.com/fisothemes/pyesys/tree/master/examples