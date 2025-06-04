import pytest
import asyncio
import gc
import time

from pyesys.prop import event


# ---------------- Module-level @event tests ----------------

def test_module_level_emitter_runs_sync_handlers_immediately_and_async_in_background(tmp_path):
    calls = []

    @event
    def on_mod(x, y):
        pass

    @on_mod.emitter
    def do_emit(x, y):
        calls.append(("emit", x, y))

    def handler_sync(a, b):
        calls.append(("sync", a, b))

    async def handler_async(a, b):
        # Simulate a very short async wait
        await asyncio.sleep(0)
        calls.append(("async", a, b))

    # Subscribe both
    on_mod += handler_sync
    on_mod += handler_async

    # Trigger emitter in sync context
    do_emit(3, "foo")
    # Sync handler must have run by now
    assert ("emit", 3, "foo") in calls
    assert ("sync", 3, "foo") in calls

    # The async handler should run in background shortly
    time.sleep(0.05)
    assert ("async", 3, "foo") in calls

    # Unsubscribe sync handler, clear calls
    on_mod -= handler_sync
    calls.clear()
    do_emit(7, "bar")
    # Only emitter and async handler should run
    assert ("emit", 7, "bar") in calls
    assert ("sync", 7, "bar") not in calls
    time.sleep(0.05)
    assert ("async", 7, "bar") in calls


@pytest.mark.asyncio
async def test_module_level_async_emitter_awaits_all_handlers():
    calls = []

    @event
    def on_mod_async(a):
        pass

    @on_mod_async.emitter
    async def emit_mod(a):
        calls.append(("emit", a))

    async def handler(a):
        await asyncio.sleep(0)
        calls.append(("h", a))

    on_mod_async += handler

    # Awaiting emitter should also wait for handler
    await emit_mod(9)
    assert ("emit", 9) in calls
    assert ("h", 9) in calls


def test_module_level_signature_mismatch_raises():
    @event
    def on_sig(a, b):
        pass

    with pytest.raises(TypeError):
        on_sig += lambda a: None  # wrong number of args


# ---------------- Class-level @event tests ----------------

class DummyButton:
    @event
    def on_click(self, value):
        pass

    @on_click.emitter
    def click(self, value):
        # do nothing else
        self._val = value


class DummyAsyncButton:
    @event
    def on_ready(self):
        pass

    @on_ready.emitter
    async def ready(self):
        await asyncio.sleep(0)


def test_class_level_events_are_per_instance():
    b1 = DummyButton()
    b2 = DummyButton()
    results = []

    def handler(value):
        # The handler doesn’t get `self`, only `value`
        results.append(value)

    b1.on_click += handler
    b2.on_click += handler

    b1.click(42)
    assert 42 in results
    results.clear()
    b2.click(99)
    assert 99 in results

    # Ensure b1’s handlers didn’t fire when b2 clicked (no mixing)
    results.clear()
    b1.click(111)
    assert results == [111]


def test_class_level_unsubscribe_works_and_signature_checked():
    b = DummyButton()
    calls = []

    def handler_ok(v):
        calls.append(v)

    # Subscribe, emit once, then unsubscribe, then emit again
    b.on_click += handler_ok
    b.click(5)
    assert calls == [5]

    b.on_click -= handler_ok
    calls.clear()
    b.click(6)
    assert calls == []

    # Trying to subscribe wrong signature raises
    with pytest.raises(TypeError):
        b.on_click += lambda: None


def test_class_level_memory_cleanup_of_bound_handlers():
    b = DummyButton()

    class Holder:
        def __init__(self):
            self.called = False

        def cb(self, val):
            self.called = True

    h = Holder()
    b.on_click += h.cb
    # Forcing creation of the Event instance
    assert hasattr(b, 'on_click')

    # Delete the holder and force GC
    del h
    gc.collect()

    # Emitting should not raise, and handler_count should drop to 0
    b.click(123)
    # Access the listener to check handler_count
    # listener is the return value of b.on_click (the descriptor)
    listener = b.on_click
    assert listener.handler_count() == 0


@pytest.mark.asyncio
async def test_class_level_async_emitter_with_mixed_handlers():
    b = DummyAsyncButton()
    results = []

    def sync_h():
        results.append("sync")

    async def async_h():
        await asyncio.sleep(0)
        results.append("async")

    b.on_ready += sync_h
    b.on_ready += async_h

    await b.ready()
    assert "sync" in results
    assert "async" in results


def test_prefixing_subscribe_on_class_directly_raises_attribute_error():
    # Attempting to do DummyButton.on_click += handler should raise
    with pytest.raises(AttributeError):
        DummyButton.on_click += lambda v: None
