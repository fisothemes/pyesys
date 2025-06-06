import gc
import pytest
import asyncio
import inspect

from pyesys.event import Event, create_event


# -------------- Factory / Signature‐Checking --------------

def test_create_event_returns_event_and_listener():
    # Using a simple example signature
    event_obj, listener = create_event(example=lambda a, b: None)
    assert isinstance(event_obj, Event)
    # The listener should have a .__iadd__ operator
    assert hasattr(listener, "__iadd__")
    assert hasattr(listener, "__isub__")


def test_create_event_non_callable_example_raises_type_error():
    with pytest.raises(TypeError):
        create_event(example=123)  # not callable


def test_listener_plus_non_callable_raises():
    event_obj, listener = create_event(example=lambda x: None)
    with pytest.raises(TypeError):
        listener += 123  # 123 is not callable


# -------------- Subscription / Unsubscription --------------

def test_subscribe_and_emit_sync_handler():
    calls = []
    event_obj, listener = create_event(example=lambda x, y: None)

    def on_data(x, y):
        calls.append((x, y))

    listener += on_data
    assert event_obj.handler_count() == 1
    event_obj.emit(10, "foo")
    assert calls == [(10, "foo")]


def test_unsubscribe_nonexistent_handler_does_not_raise():
    calls = []
    event_obj, listener = create_event(example=lambda x: None)

    def fn(x):
        calls.append(x)

    # Unsubscribing before subscribing should silently do nothing
    listener -= fn
    assert event_obj.handler_count() == 0
    # Subscribing once and unsubscribing twice
    listener += fn
    listener -= fn
    listener -= fn
    assert event_obj.handler_count() == 0


def test_unsubscribe_after_subscribe_and_emit():
    calls = []
    event_obj, listener = create_event(example=lambda x: None)

    def fn(x):
        calls.append(x)

    listener += fn
    assert event_obj.handler_count() == 1
    event_obj.emit(5)
    assert calls == [5]

    listener -= fn
    calls.clear()
    assert event_obj.handler_count() == 0
    event_obj.emit(7)
    assert calls == []


def test_allow_duplicates_false_prevents_duplicate_subscriptions():
    calls = []
    event_obj, listener = create_event(example=lambda x: None, allow_duplicates=False)

    def fn(x):
        calls.append(x)

    listener += fn
    listener += fn
    # Should only be counted once
    assert event_obj.handler_count() == 1
    event_obj.emit(1)
    assert calls == [1]  # only one invocation


def test_allow_duplicates_true_allows_multiple_subscriptions():
    calls = []
    event_obj, listener = create_event(example=lambda x: None, allow_duplicates=True)

    def fn(x):
        calls.append(x)

    listener += fn
    listener += fn
    # Should be counted twice
    assert event_obj.handler_count() == 2
    event_obj.emit(2)
    assert calls == [2, 2]


def test_bulk_subscription_with_list():
    from pyesys.event import create_event
    results = []
    evt, listener = create_event(example=lambda x: None)

    def h1(x): results.append(f"h1:{x}")
    def h2(x): results.append(f"h2:{x}")

    listener += [h1, h2]
    evt.emit("ok")
    assert results == ["h1:ok", "h2:ok"]

def test_bulk_subscription_with_tuple():
    from pyesys.event import create_event
    results = []
    evt, listener = create_event(example=lambda x: None)

    def h1(x): results.append(f"h1:{x}")
    def h2(x): results.append(f"h2:{x}")

    listener += (h1, h2)
    evt.emit("ok")
    assert results == ["h1:ok", "h2:ok"]

def test_bulk_subscription_with_set():
    from pyesys.event import create_event
    results = []
    evt, listener = create_event(example=lambda x: None)

    def h1(x): results.append(f"h1:{x}")
    def h2(x): results.append(f"h2:{x}")

    listener += {h1, h2}
    evt.emit("ok")

    assert set(results) == {"h1:ok", "h2:ok"}

def test_bulk_unsubscription_with_list():
    from pyesys.event import create_event
    results = []
    evt, listener = create_event(example=lambda x: None)

    def h1(x): results.append(f"h1:{x}")
    def h2(x): results.append(f"h2:{x}")

    listener += [h1, h2]
    listener -= [h1, h2]
    evt.emit("gone")
    assert results == []

def test_bulk_unsubscription_with_tuple():
    from pyesys.event import create_event
    results = []
    evt, listener = create_event(example=lambda x: None)

    def h1(x): results.append(f"h1:{x}")
    def h2(x): results.append(f"h2:{x}")

    listener += (h1, h2)
    listener -= (h1, h2)
    evt.emit("gone")
    assert results == []

def test_bulk_unsubscription_with_set():
    from pyesys.event import create_event
    results = []
    evt, listener = create_event(example=lambda x: None)

    def h1(x): results.append(f"h1:{x}")
    def h2(x): results.append(f"h2:{x}")

    listener += {h1, h2}
    listener -= {h1, h2}
    evt.emit("gone")
    assert results == []


# -------------- Signature Mismatch --------------

def test_signature_mismatch_raises_on_subscribe():
    event_obj, listener = create_event(example=lambda a, b: None)

    def too_few(a):
        pass

    def too_many(a, b, c):
        pass

    with pytest.raises(TypeError):
        listener += too_few

    with pytest.raises(TypeError):
        listener += too_many


# -------------- Error Handling / Isolation --------------

def test_error_in_one_handler_does_not_stop_others(tmp_path, capsys):
    errors = []
    def custom_eh(exc, handler_fn):
        errors.append((str(exc), handler_fn))

    event_obj, listener = create_event(example=lambda x: None, error_handler=custom_eh)

    def bad(x):
        raise ValueError("boom!")

    def good(x):
        errors.append(("good", x))

    listener += bad
    listener += good

    # Emitting should run both; bad’s exception should be caught by custom_eh, then good should still run.
    event_obj.emit(42)
    # We should see the bad exception reported
    assert any("boom!" in msg for msg, _ in errors)
    # And the good handler should have appended ("good", 42)
    assert ("good", 42) in errors


# -------------- handler_count and handlers property --------------

def test_handler_count_prunes_dead_bound_methods():
    class Foo:
        def __init__(self):
            self.called = False
        def cb(self, x): pass

    event_obj, listener = create_event(example=lambda x: None)
    foo = Foo()
    listener += foo.cb
    assert event_obj.handler_count() == 1

    # Delete the only strong reference and force GC
    del foo
    gc.collect()

    # handler_count() should prune that dead handler and return 0
    assert event_obj.handler_count() == 0
    assert len(event_obj.handlers) == 0


def test_handlers_returns_list_of_callables_and_not_live_mutable_ref():
    calls = []
    event_obj, listener = create_event(example=lambda x: None)

    def fn1(x):
        calls.append("fn1")

    def fn2(x):
        calls.append("fn2")

    listener += fn1
    listener += fn2

    snapshot = event_obj.handlers
    assert isinstance(snapshot, list)
    assert fn1 in snapshot and fn2 in snapshot

    # Mutating the returned list should not affect the event’s internal state
    snapshot.remove(fn1)
    assert fn1 in event_obj.handlers


# -------------- clear() --------------

def test_clear_removes_all_handlers():
    calls = []
    event_obj, listener = create_event(example=lambda x: None)

    def fn(x):
        calls.append(x)

    listener += fn
    listener += fn
    assert event_obj.handler_count() == 2

    event_obj.clear()
    assert event_obj.handler_count() == 0
    # After clear, even if we call emit, no one should get called
    calls.clear()
    event_obj.emit(99)
    assert calls == []


# -------------- Async emit_async with mixed handlers --------------

@pytest.mark.asyncio
async def test_emit_async_with_both_sync_and_async_handlers():
    results = []
    async def ah(x):
        # simulate a little work
        await asyncio.sleep(0)
        results.append(f"async:{x}")

    def sh(x):
        results.append(f"sync:{x}")

    event_obj, listener = create_event(example=lambda x: None)
    listener += ah
    listener += sh

    await event_obj.emit_async(7)
    # Both handlers should have run
    assert "async:7" in results
    assert "sync:7" in results


@pytest.mark.asyncio
async def test_emit_async_with_no_handlers_just_returns():
    event_obj, listener = create_event(example=lambda x: None)
    # Should not raise or hang
    await event_obj.emit_async(123)  # no handlers


def test_emit_returns_none_even_if_handler_returns_value():
    # Even if a handler returns something, emit() returns None
    event_obj, listener = create_event(example=lambda x: None)

    def returns_something(x):
        return "I shouldn’t break emit"

    listener += returns_something
    ret = event_obj.emit(5)
    assert ret is None
