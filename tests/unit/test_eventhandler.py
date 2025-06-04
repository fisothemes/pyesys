import gc
import inspect
import pytest
from pyesys.handler import EventHandler, default_error_handler


def test_eventhandler_calls_free_function_correctly():
    calls = []
    def free_fn(x, y):
        calls.append((x, y))

    handler = EventHandler(free_fn)
    assert handler.is_alive() is True
    # Synchronous call returns None
    result = handler(10, "foo")
    assert result is None
    assert calls == [(10, "foo")]


def test_eventhandler_detects_async_callable():
    async def async_fn(a):
        return a + 1

    handler = EventHandler(async_fn)
    assert handler.is_async() is True

    # Calling an async handler returns a coroutine
    coro = handler(5)
    assert inspect.iscoroutine(coro)
    # We shouldn’t await it here; just ensure it’s a coroutine
    coro.close()


def test_eventhandler_bound_method_is_alive_and_get_callback():
    class Dummy:
        def __init__(self):
            self.called = False

        def cb(self, value):
            self.called = True
            return "done"

    d = Dummy()
    handler = EventHandler(d.cb)
    # Bound method: should be alive
    assert handler.is_alive() is True
    callback = handler.get_callback()
    assert callback is not None
    # Calling the reconstructed bound method works
    result = callback(42)
    assert d.called is True
    assert result == "done"


def test_eventhandler_bound_method_cleanup_after_gc():
    class Dummy:
        def __init__(self):
            self.called = False

        def cb(self, v):
            self.called = True

    d = Dummy()
    handler = EventHandler(d.cb)
    assert handler.is_alive() is True

    # Remove strong reference and force GC
    del d
    gc.collect()
    assert handler.is_alive() is False

    # Calling the handler now returns None and does not raise
    result = handler(99)
    assert result is None
    # get_callback() now returns None
    assert handler.get_callback() is None


def test_eventhandler_equality_and_hash_for_free_functions():
    def f1(x): pass
    def f2(x): pass

    h1 = EventHandler(f1)
    h1_dup = EventHandler(f1)
    h2 = EventHandler(f2)

    assert h1 == h1_dup
    assert hash(h1) == hash(h1_dup)

    assert h1 != h2
    assert hash(h1) != hash(h2)


def test_eventhandler_equality_and_hash_for_bound_methods_same_instance():
    class A:
        def cb(self, x): pass

    a = A()
    h1 = EventHandler(a.cb)
    h2 = EventHandler(a.cb)
    assert h1 == h2
    assert hash(h1) == hash(h2)


def test_eventhandler_equality_for_bound_methods_different_instances():
    class A:
        def cb(self, x): pass

    a1 = A()
    a2 = A()
    h1 = EventHandler(a1.cb)
    h2 = EventHandler(a2.cb)
    assert h1 != h2


def test_eventhandler_repr_for_free_function_and_bound_method(tmp_path, capsys):
    def my_fn(x):
        return x * 2

    h_free = EventHandler(my_fn)
    repr_str = repr(h_free)
    assert "EventHandler" in repr_str
    assert "my_fn" in repr_str

    class A:
        def cb(self): pass

    a = A()
    h_bound = EventHandler(a.cb)
    repr_bound = repr(h_bound)
    # It should mention "bound method" and the class name
    assert "bound method" in repr_bound
    assert "A" in repr_bound


def test_eventhandler_get_info_structure():
    def f(x): pass
    h = EventHandler(f)
    info = h.get_info()
    assert isinstance(info, dict)
    # Must contain keys: function, function_name, is_bound_method, is_alive, is_async
    assert set(info.keys()) >= {"function", "function_name", "is_bound_method", "is_alive", "is_async"}
    assert info["function_name"] == "f"
    assert info["is_bound_method"] is False
    assert info["is_alive"] is True
    assert info["is_async"] is False
