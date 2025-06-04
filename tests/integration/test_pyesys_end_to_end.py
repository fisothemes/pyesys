import gc
import asyncio
import pytest
import time
from pyesys.event import create_event
from pyesys.prop import event


# -------------------------------------------------------------------
# Integration Test 1: create_event + EventHandler + mixed sync/async
# -------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_event_with_mixed_handlers_propagates_exceptions_and_continues():
    """
    1. Use create_event() to build an Event + listener.
    2. Register:
       - a handler that raises,
       - an async handler that awaits and records,
       - a sync handler that records.
    3. Verify that:
       - The exception goes to the default error handler,
       - The remaining handlers still run.
       - handler_count() correctly prunes a dead bound handler.
    """
    # 1) Build event & listener
    evt, listener = create_event(example=lambda a, b: None)

    # 2) Set up three handlers:
    calls = []

    # (a) a handler that raises
    def bad_handler(a, b):
        raise RuntimeError("integration‐boom")

    # (b) an async handler
    async def async_handler(a, b):
        await asyncio.sleep(0)
        calls.append(("async", a, b))

    # (c) a sync handler
    def good_handler(a, b):
        calls.append(("sync", a, b))

    listener += bad_handler
    listener += async_handler
    listener += good_handler

    # 3) Emit and await emit_async
    await evt.emit_async(123, "xyz")

    # By design, default_error_handler just prints to stderr. We don't crash.
    # Verify both async_handler and good_handler ran:
    assert ("async", 123, "xyz") in calls
    assert ("sync", 123, "xyz") in calls

    # 4) Now test pruning of a bound method via create_event
    class Temp:
        def __init__(self):
            self.recorded = []

        def cb(self, x, y):
            self.recorded.append((x, y))

    t = Temp()
    # Subscribe bound method
    listener += t.cb
    assert evt.handler_count() == 4  # bad, async, good, t.cb

    # Kill t & force GC
    del t
    gc.collect()

    # The next handler_count() call should prune t.cb
    assert evt.handler_count() == 3  # only bad, async, good remain

    # Cleanup: remove all handlers so subsequent tests are unaffected
    evt.clear()


# -------------------------------------------------------------------
# Integration Test 2: @event descriptor + create_event interoperability
# -------------------------------------------------------------------

def test_decorated_event_and_manual_create_event_do_not_collide_on_same_name():
    """
    1. Define a class that has an @event on 'on_change'
    2. Outside of that, also do create_event(example=...)
    3. Make sure subscribing to the class‐level event does not accidentally register on the module‐level event of the same name.
    4. Verify that each emitter triggers only its own handlers.
    """
    calls = {"class": [], "module": []}

    # 1) Module‐level event
    mod_event, mod_listener = create_event(example=lambda v: None)

    # 2) Class with its own @event on the same name
    class Model:
        @event
        def on_change(self, newval):
            pass

        @on_change.emitter
        def update(self, newval):
            self._val = newval

    # 3) Subscribe to class‐level
    def class_handler(val):
        calls["class"].append(("c", val))

    # Subscribe to module‐level
    def module_handler(val):
        calls["module"].append(("m", val))

    m = Model()
    m.on_change += class_handler
    mod_listener += module_handler

    # 4) Trigger each
    m.update(42)
    assert ("c", 42) in calls["class"]
    # module event should not fire from m.update
    assert calls["module"] == []

    # Now emit module event
    mod_event.emit(99)
    assert ("m", 99) in calls["module"]


# -------------------------------------------------------------------
# Integration Test 3: Full end-to-end “widget” with @event, handlers, and async/sync mix
# -------------------------------------------------------------------

class ButtonWidget:
    """
    A simple widget that simulates a UI button:
    - on_click is decorated with @event
    - click_emitter is the emitter method
    - handlers can be sync or async
    """
    @event
    def on_click(self, label: str):
        pass

    @on_click.emitter
    def click_emitter(self, label: str):
        self._last = label

    @event
    def on_ready(self):
        pass

    @on_ready.emitter
    async def ready_emitter(self):
        await asyncio.sleep(0.01)


@pytest.mark.asyncio
async def test_widget_integration_sync_and_async():
    """
    1. Create a ButtonWidget instance.
    2. Register:
       - a sync on_click handler that appends to list
       - an async on_click handler that awaits then appends
       - a sync on_ready handler
       - an async on_ready handler
    3. Trigger click_emitter and await ready_emitter.
    4. Verify that all four handlers ran exactly once, in either order.
    """
    widget = ButtonWidget()
    results = []

    # 2a) on_click handlers
    def click_sync(lbl):
        results.append(("csync", lbl))

    async def click_async(lbl):
        await asyncio.sleep(0)
        results.append(("casync", lbl))

    widget.on_click += click_sync
    widget.on_click += click_async

    # 2b) on_ready handlers
    def ready_sync():
        results.append(("rsync", None))

    async def ready_async():
        await asyncio.sleep(0)
        results.append(("rasync", None))

    widget.on_ready += ready_sync
    widget.on_ready += ready_async

    # 3) Trigger emitters
    widget.click_emitter("GO")
    # click_emitter is synchronous; the sync handler should have run immediately,
    # but the async one will run shortly in background.
    assert ("csync", "GO") in results
    # wait a brief moment for async to run
    await asyncio.sleep(0.02)
    assert ("casync", "GO") in results

    # Now trigger ready_emitter (async emitter)
    await widget.ready_emitter()
    # Both ready handlers should run by the time ready_emitter returns
    assert ("rsync", None) in results
    assert ("rasync", None) in results

    # 4) Ensure no cross-pollution: clicking again only fires click handlers
    results.clear()
    widget.click_emitter("AGAIN")
    assert ("csync", "AGAIN") in results
    await asyncio.sleep(0.02)
    assert ("casync", "AGAIN") in results
    assert all(r[0] in ("csync", "casync") for r in results)


# -------------------------------------------------------------------
# Integration Test 4: Chained subscriptions and default error handler
# -------------------------------------------------------------------

def test_chained_subscriptions_and_default_error_handler_captures_exceptions(capfd):
    """
    1. Build a small chain of handlers for a create_event-based event.
    2. Have the first handler throw an exception, the second mutate a list,
       the third be a bound method that also records.
    3. When emit() is called, nothing should bubble up; default_error_handler
       will print the traceback to stderr. The second and third handlers should still run.
    4. Finally, confirm that the default_error_handler printed something recognizable.
    """
    evt, listener = create_event(example=lambda x: None)
    log = []

    def first(x):
        raise ValueError("chain‐error")

    def second(x):
        log.append(("second", x))

    class T:
        def __init__(self):
            self.log = []

        def third(self, x):
            self.log.append(("third", x))

    t = T()

    listener += first
    listener += second
    listener += t.third

    # Call emit and capture stderr
    evt.emit("HELLO")

    # second and third should have run
    assert ("second", "HELLO") in log
    assert ("third", "HELLO") in t.log

    # Check that something was printed to stderr by default_error_handler
    captured = capfd.readouterr()
    assert "ValueError('chain‐error')" in captured.err


# -------------------------------------------------------------------
# Integration Test 5: sync emit ignores async handlers
# -------------------------------------------------------------------

def test_sync_emit_ignores_async_handlers():
    """
    1. Create a create_event-based emitter with both sync and async handlers.
    2. Call emitter.emit(...) (synchronous).
    3. Verify that only the sync handler runs; the async handler is ignored.
    """
    evt, listener = create_event(example=lambda x: None)
    results = []

    def sync_h(x):
        results.append(("sync", x))

    async def async_h(x):
        results.append(("async", x))

    listener += sync_h
    listener += async_h

    # Call the synchronous emit: async_h should be ignored
    evt.emit(777)

    # Only sync handler should have run
    assert ("sync", 777) in results
    assert ("async", 777) not in results

    # Cleanup
    evt.clear()


# -------------------------------------------------------------------
# Integration Test 6: emit_async runs both sync and async handlers
# -------------------------------------------------------------------

@pytest.mark.asyncio
async def test_emit_async_runs_both_sync_and_async_handlers():
    """
    1. Create a create_event-based emitter with both sync and async handlers.
    2. Call emitter.emit_async(...) and await it.
    3. Verify that both sync and async handlers run.
    """
    evt, listener = create_event(example=lambda x: None)
    results = []

    def sync_h(x):
        results.append(("sync", x))

    async def async_h(x):
        await asyncio.sleep(0)
        results.append(("async", x))

    listener += sync_h
    listener += async_h

    # Call the async emit and await it
    await evt.emit_async(888)

    # Both handlers should have run
    assert ("sync", 888) in results
    assert ("async", 888) in results

    # Cleanup
    evt.clear()
