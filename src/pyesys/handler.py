import weakref
import inspect
from types import MethodType
from typing import Callable, Optional, Protocol, ParamSpec, Any, Union, Coroutine

P = ParamSpec("P")  # Parameter specification for handler arguments


class ErrorHandler(Protocol):
    """
    Protocol for custom error handlers used in event emission.

    Error handlers receive exceptions that occur during handler execution
    and can implement custom logging, reporting, or recovery logic.
    """

    def __call__(
        self, exception: Exception, handler: Optional[Callable[..., None]]
    ) -> None:
        """
        Handle an exception that occurred during event handler execution.

        :param exception: The exception that was raised.
        :param handler: The handler that raised the exception (may be None if unavailable).
        """
        ...


def default_error_handler(
    exception: Exception, handler: Optional[Callable[..., None]]
) -> None:
    """
    Default error handler that prints exceptions to stderr.

    This provides basic error reporting without causing the application to crash
    when event handlers raise exceptions.

    :param exception: The exception that was raised.
    :param handler: The handler that raised the exception (may be None).
    """
    import sys

    handler_desc = repr(handler) if handler else "<unavailable>"
    print(
        f"[PyESys] Handler {handler_desc} raised exception: {exception!r}",
        file=sys.stderr,
    )


class EventHandler:
    """
    Wraps a callable handler with advanced features:

    - Weak-reference support for bound methods (prevents memory leaks)
    - Automatic cleanup when instances are garbage-collected
    - Proper equality and hashing for duplicate detection
    - Thread-safe callback reconstruction
    - Handles both sync and async callables appropriately

    This class handles the complexity of managing bound method references
    while providing a simple callable interface.
    """

    __slots__ = ("_func", "_self_ref", "_hash", "_is_async")

    def __init__(self, func: Callable[P, None]):
        """
        Initialize an EventHandler for the given callable.

        If func is a bound method, stores a weak reference to its instance
        to prevent memory leaks while allowing automatic cleanup.

        :param func: Callable to be invoked when the event is emitted.
        :raises TypeError: If func is not callable.
        """
        if not callable(func):
            raise TypeError(f"Handler must be callable, got {type(func)}")

        if hasattr(func, "__self__") and func.__self__ is not None:
            # Bound method: store underlying function and weakref to instance
            self._func = func.__func__  # The actual unbound function
            self._self_ref = weakref.ref(func.__self__)  # Weak ref to instance
            self._hash = hash((self._func, func.__self__))
            # Check if the underlying function is async
            self._is_async = inspect.iscoroutinefunction(self._func)
        else:
            # Unbound function or static method: store function directly
            self._func = func
            self._self_ref = None
            self._hash = hash((self._func, None))
            self._is_async = inspect.iscoroutinefunction(func)

    def __call__(
        self, *args: P.args, **kwargs: P.kwargs
    ) -> Union[None, Coroutine[Any, Any, None]]:
        """
        Invoke the underlying callable if it's still alive.

        For bound methods, this checks if the instance still exists.
        If the instance has been garbage-collected, this becomes a no-op.

        For async callables, this returns a coroutine that the caller must handle.

        :param args: Positional arguments matching ParamSpec P.
        :param kwargs: Keyword arguments matching ParamSpec P.
        :return: None for sync callables, Coroutine for async callables, or None if dead.
        """
        if self._self_ref is not None:
            # Bound method: check if instance is still alive
            instance = self._self_ref()
            if instance is None:
                # Instance was garbage-collected, handler is dead
                return None

            # Reconstruct bound method and call it
            if self._is_async:
                # Return the coroutine for the caller to handle
                return self._func(instance, *args, **kwargs)
            else:
                # Regular sync bound method
                self._func(instance, *args, **kwargs)
                return None
        else:
            # Regular function: call directly
            if self._is_async:
                # Return the coroutine for the caller to handle
                return self._func(*args, **kwargs)
            else:
                # Regular sync function
                self._func(*args, **kwargs)
                return None

    def is_alive(self) -> bool:
        """
        Check if this handler is still alive and can be invoked.

        :return: False if it was a bound method and the instance is gone, True otherwise.
        """
        if self._self_ref is not None:
            return self._self_ref() is not None
        return True

    def is_async(self) -> bool:
        """
        Check if this handler is async (coroutine function).

        :return: True if the handler is async.
        """
        return self._is_async

    def get_callback(self) -> Optional[Callable[P, None]]:
        """
        Return the current callable, reconstructing bound methods if necessary.

        This method handles the complexity of recreating bound methods from
        their components while checking for instance liveness.

        :return: The original function or bound method, or None if dead.
        """
        if self._self_ref is not None:
            # Bound method: check instance and reconstruct if alive
            instance = self._self_ref()
            if instance is None:
                return None
            return MethodType(self._func, instance)
        # Regular function: return as-is
        return self._func

    def __eq__(self, other: object) -> bool:
        """
        Compare two EventHandler instances for equality based on function and instance.

        Two handlers are equal if they wrap the same function and the same instance
        (for bound methods) or the same function (for unbound functions).

        :param other: Another object to compare.
        :return: True if both wrap the same function and instance (if any).
        """
        if not isinstance(other, EventHandler):
            return False

        # Functions must be the same
        if self._func is not other._func:
            return False

        # Both are unbound functions
        if self._self_ref is None and other._self_ref is None:
            return True

        # Both are bound methods - compare instances
        if self._self_ref is not None and other._self_ref is not None:
            self_instance = self._self_ref()
            other_instance = other._self_ref()

            # If either instance is dead, they're not equal to anything
            if self_instance is None or other_instance is None:
                return False

            return self_instance is other_instance

        # One is bound, one is unbound - not equal
        return False

    def __hash__(self) -> int:
        """
        Hash based on the underlying function and instance (or None).

        The hash is computed at initialization time to ensure consistency
        even if the instance is later garbage-collected.

        :return: Cached hash value.
        """
        return self._hash

    def __repr__(self) -> str:
        """
        String representation for debugging and logging.

        :return: Human-readable representation of this EventHandler.
        """
        callback = self.get_callback()
        if callback is None:
            return f"EventHandler(<dead bound method>)"

        async_marker = " async" if self._is_async else ""

        if self._self_ref is not None:
            instance = self._self_ref()
            if instance is not None:
                return f"EventHandler(<{async_marker} bound method {self._func.__name__} of {instance!r}>)"
            else:
                return f"EventHandler(<dead{async_marker} bound method {self._func.__name__}>)"
        else:
            return f"EventHandler({async_marker} {self._func!r})"

    def get_info(self) -> dict[str, Any]:
        """
        Get detailed information about this handler for debugging purposes.

        :return: Dictionary containing handler information.
        """
        info = {
            "function": self._func,
            "function_name": getattr(self._func, "__name__", "<unknown>"),
            "is_bound_method": self._self_ref is not None,
            "is_alive": self.is_alive(),
            "is_async": self._is_async,
        }

        if self._self_ref is not None:
            instance = self._self_ref()
            info.update(
                {
                    "instance": instance,
                    "instance_type": type(instance).__name__ if instance else "<dead>",
                }
            )

        return info
