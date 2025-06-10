Usage Guide
===========

This guide shows how to use PyESys to:

- Create and emit events
- Subscribe sync or async handlers
- Use `@event` decorators (class/module level)
- Bulk subscribe/unsubscribe
- Chain events
- Handle errors safely

----

Installation
------------

PyESys requires Python 3.12+.

.. code-block:: bash

   pip install pyesys

Or for local development:

.. code-block:: bash

   git clone https://github.com/fisothemes/pyesys.git
   cd pyesys
   pip install -e .[dev]

----

Creating and Emitting Events
----------------------------

Use `create_event(...)` with a sample function that defines the expected handler signature:

.. code-block:: python

   from pyesys import create_event

   event, listener = create_event(example=lambda x: None)

   def handler(x):
       print("Handled:", x)

   listener += handler
   event.emit(42)

Here, any handler must accept one argument. The event runs all subscribed handlers safely when `emit(...)` is called.

----

Using `@event` at Module Level
------------------------------

You can define reusable global events using `@event`:

.. code-block:: python

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

This sets up a global event `on_hello`, whose emitter `hello()` runs the body, then automatically fires all subscribed handlers with the same arguments.

----

Using `@event` at Class Level
-----------------------------

Class-level events are **per instance**, like `.NET` or GUI frameworks:

.. code-block:: python

   from pyesys import event

   class Button:
       @event
       def on_click(self): ...

       @on_click.emitter
       def click(self):
           print("Button clicked!")

   b = Button()
   b.on_click += lambda: print("Handler called!")
   b.click()

Each `Button` instance gets its own `on_click` event. The `click()` method prints a message and then automatically triggers the event.

----

Bulk Subscribe and Unsubscribe
------------------------------

You can add/remove multiple handlers at once using lists, sets, or tuples:

.. code-block:: python

   def a(x): ...
   def b(x): ...
   def c(x): ...

   listener += [a, b, c]     # Add all
   listener -= {a, b}        # Remove some

This makes it easy to bind or unbind groups of related callbacks without looping.

----

Chaining Events Across Instances
--------------------------------

You can chain events from one class to another, great for pipelines or steps:

.. code-block:: python

   from pyesys import event
   from abc import ABC

   class Step(ABC):
       @event
       def on_done(self, data): ...

       @on_done.emitter
       def done(self, data=None): ...

   class StepOne(Step):
       def run(self, data=None):
           print("Step 1: Doing work...")
           self.done("data-from-step-1")

   class StepTwo(Step):
       def run(self, input_data: str):
           print(f"Step 2: Received '{input_data}', doing more work...")
           self.done("result-from-step-2")

   class StepThree(Step):
       def run(self, result: str):
           print(f"Step 3: Finalising with result '{result}'")
           self.done()

   s1, s2, s3 = StepOne(), StepTwo(), StepThree()

   s1.on_done += s2.run
   s2.on_done += s3.run

   s1.run()

**What happens**:
1. `s1.run()` emits `"data-from-step-1"`
2. `s2.run(...)` receives it, does work, emits its result
3. `s3.run(...)` gets the final result

This pattern models pipelines, workflows, and signal propagation.

----

Async Handlers with `emit_async`
--------------------------------

Mix sync and async handlers freely. Use `emit_async()` to await all:

.. code-block:: python

   import asyncio

   async def async_handler(x):
       await asyncio.sleep(0.1)
       print("async", x)

   def sync_handler(x):
       print("sync", x)

   listener += [sync_handler, async_handler]
   asyncio.run(event.emit_async(5))

Sync handlers run in a thread pool. Async ones are awaited properly. This is safe and parallel by design.

----

Custom Error Handling
---------------------

Define your own handler for exceptions raised by subscribers:

.. code-block:: python

   def custom_handler(exc, handler):
       print(f"ERROR: {handler} raised {exc}")

   event, listener = create_event(
       example=lambda x: None,
       error_handler=custom_handler
   )

   def bad(x): raise RuntimeError("fail")
   listener += bad
   event.emit(10)

The event will still run remaining handlers. By default, errors are printed to `stderr`.

----

Clearing and Introspection
--------------------------

You can query or clear handlers any time:

.. code-block:: python

   print(listener.handler_count())  # active handlers
   for h in event.handlers:
       print(h)

   event.clear()
   assert listener.handler_count() == 0

----

More Examples
-------------

You can find more complete usage examples in the GitHub repository:

🔗 https://github.com/fisothemes/pyesys/tree/master/examples

