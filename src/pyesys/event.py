import threading
import inspect
import asyncio
import weakref
import gc
from typing import Callable, List, Tuple, Optional, Union, Iterable, Coroutine, Any
from concurrent.futures import Future

from .handler import EventHandler, ErrorHandler, default_error_handler, P


class Event:
    """
    A thread-safe event dispatcher with comprehensive features:

    - Weak-reference support for bound methods (automatic cleanup)
    - Runtime signature checking via example function
    - Configurable error handling with consistent behavior
    - Introspection: handler_count, handlers list
    - Duplicate subscription control
    - Mixed sync/async support with proper resource management
    - Performance optimizations with lazy cleanup

    Generic P: parameter specification for handler arguments.
    """

    class Listener:
        """
        Provides a restricted interface to subscribe/unsubscribe handlers
        to the outer Event without exposing emission or clearing capabilities.

        This separation ensures subscribers cannot accidentally trigger events
        or clear all handlers.
        """

        __slots__ = ("_outer", "_per_instance")

        def __init__(self, outer: "Event"):
            """
            Initialize a Listener for a given Event.

            :param outer: The Event instance to subscribe to.
            """
            self._outer = outer
            self._per_instance = None  # Set by EventDescriptor for introspection

        def __iadd__(self, handler: Union[Callable[P, None], Iterable[Callable[P, None]]]) -> "Event.Listener":
            """
            Subscribe one or more handlers to the Event.

            Supports single callables or iterables (list, tuple, set).

            :param handler: Callable or iterable of callables to subscribe.
            :return: Self for chaining.
            :raises TypeError: If handler is not callable.
            """
            self._outer += handler
            return self

        def __isub__(self, handler: Union[Callable[P, None], Iterable[Callable[P, None]]]) -> "Event.Listener":
            """
            Unsubscribe one or more handlers from the Event.

            Supports single callables or iterables (list, tuple, set).

            :param handler: Callable or iterable of callables to unsubscribe.
            :return: Self for chaining.
            :raises TypeError: If handler is not callable.
            """
            self._outer -= handler
            return self

        def subscribe(self, handler: Callable[P, None]) -> None:
            """
            Alternative to += operator for subscribing handlers.

            :param handler: Callable to subscribe.
            :raises TypeError: If handler is not callable.
            """
            self._outer += handler

        def unsubscribe(self, handler: Union[Callable[P, None], Iterable[Callable[P, None]]]) -> None:
            """
            Alternative to -= operator for unsubscribing handlers.

            Supports single callables or iterables (list, tuple, set).

            :param handler: Callable or iterable of callables to unsubscribe.
            :raises TypeError: If handler is not callable.
            """
            self._outer -= handler

        def handler_count(self) -> int:
            """
            Number of currently alive handlers.

            :return: Count of active handlers.
            """
            return self._outer.handler_count()

    def __init__(
        self,
        *,
        allow_duplicates: bool = True,
        error_handler: Optional[ErrorHandler] = None,
    ):
        """
        Initialize an Event with no handlers.

        :param allow_duplicates: If True, the same handler can be added multiple times.
        :param error_handler: Custom error handler, or None for default behavior.
        """
        self._handlers: List[EventHandler] = []
        self._lock = threading.RLock()  # RLock for potential recursive calls
        self.listener = Event.Listener(self)
        self._sig: Optional[inspect.Signature] = None
        self._allow_duplicates = allow_duplicates
        self._error_handler = error_handler or default_error_handler
        self._cleanup_counter = 0  # For optimized cleanup

    @staticmethod
    def _is_signature_compatible(
        sig: inspect.Signature, expected_sig: inspect.Signature
    ) -> bool:
        """
        Determine if two signatures are compatible in parameter count and kinds,
        ignoring type annotations.

        :param sig: Signature of a handler to check.
        :param expected_sig: Expected signature to compare against.
        :return: True if signatures are compatible.
        """
        sig_params = list(sig.parameters.values())
        expected_params = list(expected_sig.parameters.values())

        if len(sig_params) != len(expected_params):
            return False

        for p, q in zip(sig_params, expected_params):
            if p.kind != q.kind:
                return False
        return True

    def _cleanup_dead_handlers(self, force: bool = False) -> None:
        """
        Remove dead handlers from the internal list with performance optimization.

        Uses lazy cleanup strategy to avoid overhead on every operation.
        Must be called with lock held.

        :param force: If True, always perform cleanup regardless of counter.
        """
        if not force:
            self._cleanup_counter += 1

        # Perform cleanup every 10 operations, on first operation, or when forced
        should_cleanup = force or (
            self._cleanup_counter == 1 or self._cleanup_counter % 10 == 0
        )

        if should_cleanup:
            original_count = len(self._handlers)

            # Force multiple garbage collection cycles for more reliable cleanup
            if original_count > 0:
                for _ in range(3):  # Multiple cycles for thorough cleanup
                    gc.collect()

            # Filter out dead handlers
            alive_handlers = []
            for h in self._handlers:
                if h.is_alive():
                    alive_handlers.append(h)

            self._handlers[:] = alive_handlers

            # Reset counter if we actually cleaned up something
            if len(self._handlers) < original_count:
                self._cleanup_counter = 0

    def _validate_handler(self, handler: Callable[P, None]) -> None:
        """
        Validate that a handler is callable and has compatible signature.

        :param handler: Handler to validate.
        :raises TypeError: If handler is invalid or incompatible.
        """
        if not callable(handler):
            raise TypeError(f"Handler must be callable, got {type(handler)}")

        if self._sig:
            try:
                # Handle bound methods - drop their first parameter before comparing
                if hasattr(handler, "__self__") and handler.__self__ is not None:
                    full_sig = inspect.signature(handler.__func__)
                    params = list(full_sig.parameters.values())[1:]  # drop 'self'
                    handler_sig = full_sig.replace(parameters=params)
                else:
                    handler_sig = inspect.signature(handler)

                if not Event._is_signature_compatible(handler_sig, self._sig):
                    raise TypeError(
                        f"Handler signature {handler_sig} is not compatible with "
                        f"expected {self._sig}"
                    )
            except (ValueError, TypeError) as e:
                raise TypeError(f"Cannot inspect handler signature: {e}")

    def subscribe_one(self, handler: Callable[P, None]) -> None:
        """ 
        Subscribe a single handler to this Event with validation and duplicate control.

        Performs runtime signature checking.

        :param handler: Callable to subscribe.
        :raises TypeError: If handler is invalid or incompatible.
        """
        self._validate_handler(handler)

        h = handler if isinstance(handler, EventHandler) else EventHandler(handler)
        with self._lock:
            if self._allow_duplicates or h not in self._handlers:
                self._handlers.append(h)

    def unsubscribe_one(self, handler: Callable[P, None]) -> None:
        """
        Unsubscribe a single handler from this Event.

        :param handler: Callable previously subscribed.
        :raises TypeError: If handler is not callable.
        """
        if not callable(handler):
            raise TypeError(f"Handler must be callable, got {type(handler)}")
        
        h = handler if isinstance(handler, EventHandler) else EventHandler(handler)
        with self._lock:
            try:
                self._handlers.remove(h)
            except ValueError:
                pass # Handler not found, ignore silently

    def __iadd__(self, handler: Union[Callable[P, None], Iterable[Callable[P, None]]]) -> "Event":
        """
        Subscribe one or more handlers to this Event with validation and duplicate control.

        Supports single callables or iterables (list, tuple, set).

        Performs runtime signature checking.

        :param handler: Callable or iterable of callables to subscribe.
        :return: Self for chaining.
        :raises TypeError: If handler is invalid or incompatible.
        """
        if isinstance(handler, (list, tuple, set)):
            for h in handler:
                self._subscribe_one(h)
        else:
            self._subscribe_one(handler)
        return self

    def __isub__(self, handler: Union[Callable[P, None], Iterable[Callable[P, None]]]) -> "Event":
        """
        Unsubscribe one or more handlers from this Event.

        Supports single callables or iterables (list, tuple, set).

        If duplicates exist, only the first matching handler is removed.

        :param handler: Callable or iterable of callables to unsubscribe.
        :return: Self for chaining.
        :raises TypeError: If handler is not callable.
        """
        if isinstance(handler, (list, tuple, set)):
            for h in handler:
                self._unsubscribe_one(h)
        else:
            self._unsubscribe_one(handler)
        return self

    def emit(self, *args: P.args, **kwargs: P.kwargs) -> None:
        """
        Emit the event synchronously, invoking all subscribed handlers.

        Error handling isolates exceptions: one handler's exception does not
        prevent others from running. Dead bound-method handlers are automatically
        removed during cleanup.

        Async handlers that return coroutines are silently ignored in sync emission.

        :param args: Positional arguments matching signature P.
        :param kwargs: Keyword arguments matching signature P.
        """
        with self._lock:
            # Optimized cleanup and snapshot for iteration
            self._cleanup_dead_handlers()
            handlers_snapshot = list(self._handlers)

        # Invoke each handler with consistent error handling
        for h in handlers_snapshot:
            try:
                result = h(*args, **kwargs)
                # If handler returned a coroutine, we can't await it in sync context
                # Just ignore it - this is expected behavior for mixed sync/async events
                if inspect.iscoroutine(result):
                    result.close()  # Properly close the coroutine to avoid warnings
            except Exception as e:
                callback = h.get_callback()
                if callback is not None:  # Only report errors for live handlers
                    try:
                        self._error_handler(e, callback)
                    except Exception:
                        # Prevent error handler exceptions from propagating
                        pass

    async def emit_async(self, *args: P.args, **kwargs: P.kwargs) -> None:
        """
        Asynchronously emit the event, invoking all subscribed handlers concurrently.

        Handlers that are coroutine functions will be awaited; regular callables
        will be scheduled on the default executor. All exceptions are consistently
        routed to the configured error_handler.

        :param args: Positional arguments matching signature P.
        :param kwargs: Keyword arguments matching signature P.
        """
        with self._lock:
            self._cleanup_dead_handlers()
            handlers_snapshot = list(self._handlers)

        if not handlers_snapshot:
            return

        loop = asyncio.get_running_loop()
        tasks: List[Future] = []

        for h in handlers_snapshot:
            callback = h.get_callback()
            if callback is None:
                continue

            if inspect.iscoroutinefunction(callback):
                # Handle async functions (including bound async methods)
                coroutine = callback(*args, **kwargs)
                tasks.append(
                    loop.create_task(self._wrap_async_handler(coroutine, callback))
                )
            elif hasattr(callback, "__func__") and inspect.iscoroutinefunction(
                callback.__func__
            ):
                # Handle bound methods of async functions
                coroutine = callback(*args, **kwargs)
                tasks.append(
                    loop.create_task(self._wrap_async_handler(coroutine, callback))
                )
            else:
                # Handle sync functions in thread pool
                tasks.append(
                    loop.run_in_executor(
                        None, self._wrap_sync_handler, callback, args, kwargs
                    )
                )

        if tasks:
            # Wait for all tasks to complete with consistent error handling
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _wrap_async_handler(
        self, coro: Coroutine, handler: Callable[P, None]
    ) -> None:
        """
        Await a coroutine handler and route exceptions consistently.

        :param coro: Coroutine to await.
        :param handler: Original handler function for error reporting.
        """
        try:
            await coro
        except Exception as e:
            try:
                self._error_handler(e, handler)
            except Exception:
                # Prevent error handler exceptions from propagating
                pass

    def _wrap_sync_handler(
        self, handler: Callable[P, None], args: tuple[Any, ...], kwargs: dict[str, Any]
    ) -> None:
        """
        Execute a synchronous handler and route exceptions consistently.

        :param handler: Callable to run.
        :param args: Tuple of positional arguments for the handler.
        :param kwargs: Dictionary of keyword arguments for the handler.
        """
        try:
            handler(*args, **kwargs)
        except Exception as e:
            try:
                self._error_handler(e, handler)
            except Exception:
                # Prevent error handler exceptions from propagating
                pass

    def clear(self) -> None:
        """
        Remove all subscribed handlers from this Event.

        This is useful for cleanup or resetting event state.
        """
        with self._lock:
            self._handlers.clear()
            self._cleanup_counter = 0

    def handler_count(self) -> int:
        """
        Number of currently alive handlers subscribed.

        This property triggers cleanup of dead handlers for accurate counting.

        :return: Count of active handlers.
        """
        with self._lock:
            self._cleanup_dead_handlers(force=True)
            return len(self._handlers)

    @property
    def handlers(self) -> List[Callable[P, None]]:
        """
        Return a list of currently alive handler callables.

        This property triggers cleanup and reconstructs callable references.

        :return: List of active handler functions or bound methods.
        """
        with self._lock:
            self._cleanup_dead_handlers(force=True)
            return [
                h.get_callback() for h in self._handlers if h.get_callback() is not None
            ]

    def __bool__(self) -> bool:
        """
        Return True if there are any alive handlers.

        :return: True if event has active handlers.
        """
        return self.handler_count() > 0

    def __len__(self) -> int:
        """
        Return number of alive handlers.

        :return: Count of active handlers.
        """
        return self.handler_count()

    @classmethod
    def new(
        cls,
        example: Callable[P, None],
        *,
        allow_duplicates: bool = True,
        error_handler: Optional[ErrorHandler] = None,
    ) -> Tuple["Event", "Event.Listener"]:
        """
        Factory method to create an Event with runtime signature checking.

        :param example: Example function whose signature defines allowed handler signature.
        :param allow_duplicates: If True, same handler can be subscribed multiple times.
        :param error_handler: Custom error handler for exceptions during emission.
        :return: Tuple of (Event instance, Listener interface).
        :raises TypeError: If example is not callable.
        """
        if not callable(example):
            raise TypeError(f"Example must be callable, got {type(example)}")

        e = cls(allow_duplicates=allow_duplicates, error_handler=error_handler)
        e._sig = inspect.signature(example)
        return e, e.listener


# Factory alias for brevity (signature-checked events)
create_event = Event.new
