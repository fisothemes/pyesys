import inspect
import asyncio
import weakref
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, ParamSpec, Optional, Any, Dict, Tuple, List
from .event import Event

P = ParamSpec("P")  # Parameter spec for both module and class events

# Shared thread pool for async handler execution in sync contexts
_async_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="PyESys-Async")


def _is_async_callable(func: Callable) -> bool:
    """
    Check if a callable is async, handling bound methods correctly.

    :param func: Callable to check.
    :return: True if the callable is async.
    """
    if inspect.iscoroutinefunction(func):
        return True
    # Handle bound methods - check the underlying function
    if hasattr(func, "__func__"):
        return inspect.iscoroutinefunction(func.__func__)
    return False


class EventDescriptor:
    """
    Unified descriptor for both module-level and class-level events.

    - If used at module level (no __set_name__), it holds a single global Event.
    - If used inside a class (after __set_name__), it manages a per-instance Event.

    Features:
    - Automatic signature detection and validation
    - Per-instance events for class usage
    - Global events for module usage
    - Emitter decorator pattern
    - Mixed sync/async handler support with proper resource management
    """

    def __init__(self, func: Callable[P, None]):
        """
        Initialize the EventDescriptor with a signature-defining function.

        :param func: Function whose signature defines the event parameters.
        :raises TypeError: If func is not callable.
        """
        if not callable(func):
            raise TypeError(f"Event signature must be callable, got {type(func)}")

        # Store optimized signature information instead of full signature object
        sig = inspect.signature(func)
        self._param_kinds: List[inspect.Parameter.kind] = [
            p.kind for p in sig.parameters.values()
        ]
        self._param_count: int = len(sig.parameters)
        self._original_sig = sig  # Keep for error messages and complex validation

        self._name: Optional[str] = None
        self._per_instance: weakref.WeakKeyDictionary[Any, Event] = (
            weakref.WeakKeyDictionary()
        )
        self._global_event: Optional[Event] = None
        self._cleanup_counter: int = 0

    def __set_name__(self, owner: type, name: str) -> None:
        """
        Called when class is created; switches to per-instance mode.

        :param owner: The class that owns this descriptor.
        :param name: The attribute name.
        """
        self._name = name

    def __get__(self, instance: Any, owner: type) -> Any:
        """
        Get the appropriate event listener based on access context.

        :param instance: Instance accessing the descriptor (None for class access).
        :param owner: Class owning the descriptor.
        :return: Event.Listener for subscription operations.
        """
        if instance is None:
            # Accessed on class: return this descriptor
            return self

        # Accessed on instance: return (or create) that instance's Event listener
        ev = self._per_instance.get(instance)
        if ev is None:
            # For class-level events, create signature without 'self' parameter
            if self._param_count > 0:
                # Remove first parameter (self) for class events
                class_param_kinds = self._param_kinds[1:]
                class_param_count = self._param_count - 1
            else:
                class_param_kinds = []
                class_param_count = 0

            ev, listener = Event.new(
                self._create_example_func(class_param_kinds, class_param_count)
            )
            self._per_instance[instance] = ev

            # Link the new listener back to the per-instance map for introspection
            listener._per_instance = self._per_instance
            return listener

        # Existing Event: get its listener and ensure proper linking
        listener = ev.listener
        listener._per_instance = self._per_instance
        return listener

    def _create_example_func(
        self, param_kinds: List[inspect.Parameter.kind], param_count: int
    ) -> Callable:
        """
        Create a dummy function with the specified parameter signature.

        :param param_kinds: List of parameter kinds.
        :param param_count: Number of parameters.
        :return: Callable with matching signature.
        """
        if param_count == 0:
            return lambda: None
        elif param_count == 1:
            return lambda a: None
        elif param_count == 2:
            return lambda a, b: None
        elif param_count == 3:
            return lambda a, b, c: None
        else:
            # For more complex signatures, fall back to *args
            return lambda *args: None

    def __iadd__(self, handler: Callable[P, None]) -> "EventDescriptor":
        """
        Subscribe a handler to the event.

        :param handler: Callable to subscribe.
        :return: Self for chaining.
        :raises TypeError: If handler is not callable.
        :raises AttributeError: If used incorrectly on class-level events.
        """
        if not callable(handler):
            raise TypeError(f"Handler must be callable, got {type(handler)}")

        if self._name is None:
            # Module-level usage
            if self._global_event is None:
                ev, _listener = Event.new(
                    self._create_example_func(self._param_kinds, self._param_count)
                )
                self._global_event = ev
            self._global_event += handler
            return self

        # Class-level: must use instance.event_name += handler
        raise AttributeError(
            f"Cannot subscribe to class event '{self._name}' directly. "
            f"Use 'instance.{self._name} += handler' instead."
        )

    def __isub__(self, handler: Callable[P, None]) -> "EventDescriptor":
        """
        Unsubscribe a handler from the event.

        :param handler: Callable to unsubscribe.
        :return: Self for chaining.
        :raises TypeError: If handler is not callable.
        :raises AttributeError: If used incorrectly on class-level events.
        """
        if not callable(handler):
            raise TypeError(f"Handler must be callable, got {type(handler)}")

        if self._name is None:
            # Module-level removal
            if self._global_event is not None:
                self._global_event -= handler
            return self

        # Class-level: must use instance.event_name -= handler
        raise AttributeError(
            f"Cannot unsubscribe from class event '{self._name}' directly. "
            f"Use 'instance.{self._name} -= handler' instead."
        )

    def _handle_async_handlers_in_background(
        self, event: Event, args: Tuple[Any, ...], kwargs: Dict[str, Any]
    ) -> None:
        """
        Handle async handlers in background with proper resource management.

        :param event: Event instance to emit on.
        :param args: Arguments for the event.
        :param kwargs: Keyword arguments for the event.
        """
        async_handlers = [cb for cb in event.handlers if _is_async_callable(cb)]
        if async_handlers:

            def run_async() -> None:
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(event.emit_async(*args, **kwargs))
                    finally:
                        loop.close()
                except Exception as e:
                    # Use the event's error handler for consistency
                    if hasattr(event, "_error_handler"):
                        event._error_handler(e, None)

            # Use shared thread pool for better resource management
            _async_executor.submit(run_async)

    def emitter(self, fn: Callable[P, None]) -> Callable[P, None]:
        """
        Decorator for the emitter function.
        Wraps fn so that after running its body, it fires the appropriate Event.

        :param fn: Function to wrap as an emitter.
        :return: Wrapped function that emits events after execution.
        :raises TypeError: If fn is not callable.
        """
        if not callable(fn):
            raise TypeError(f"Emitter must be callable, got {type(fn)}")

        if inspect.iscoroutinefunction(fn):

            async def async_wrapped(*args: P.args, **kwargs: P.kwargs) -> Any:
                """Async emitter wrapper that handles event emission after function execution."""
                # 1) Run original async body
                result = await fn(*args, **kwargs)

                # 2) Dispatch to event
                if self._name is None:
                    # Module-level: pass all args
                    if self._global_event is not None:
                        await self._global_event.emit_async(*args, **kwargs)
                else:
                    # Class-level: pass args without sender to handlers
                    if args:  # Ensure we have at least one argument (self)
                        inst = args[0]
                        ev = self._per_instance.get(inst)
                        if ev is not None:
                            # For class events, handlers get args minus self
                            await ev.emit_async(*args[1:], **kwargs)

                return result

            return async_wrapped
        else:

            def sync_wrapped(*args: P.args, **kwargs: P.kwargs) -> Any:
                """Sync emitter wrapper that handles event emission after function execution."""
                # 1) Run original sync body
                result = fn(*args, **kwargs)

                # 2) Dispatch to event
                if self._name is None:
                    # Module-level: pass all args
                    if self._global_event is not None:
                        self._global_event.emit(*args, **kwargs)
                        # Handle async handlers in background
                        self._handle_async_handlers_in_background(
                            self._global_event, args, kwargs
                        )
                else:
                    # Class-level: pass args without sender to handlers
                    if args:  # Ensure we have at least one argument (self)
                        inst = args[0]
                        ev = self._per_instance.get(inst)
                        if ev is not None:
                            # For class events, handlers get args minus self
                            emit_args = args[1:]
                            ev.emit(*emit_args, **kwargs)
                            # Handle async handlers in background
                            self._handle_async_handlers_in_background(
                                ev, emit_args, kwargs
                            )

                return result

            return sync_wrapped


def event(func: Callable[P, None]) -> EventDescriptor:
    """
    Decorator to create a module-level or class-level event.

    This unified decorator automatically handles both use cases:
    - When used at module level: creates a global event
    - When used in a class: creates per-instance events

    Usage:
    .. code-block:: python
        @event
        def on_something(...):
            '''Event signature definition'''
            pass

        @on_something.emitter
        def do_action(...):
            '''Action that triggers the event'''
            # Your logic here
            pass  # Event automatically emitted after this

    In a class, this becomes a per-instance event; at module level,
    it's a single global event.

    :param func: Function defining the event signature.
    :return: EventDescriptor that manages the event.
    :raises TypeError: If func is not callable.
    """
    return EventDescriptor(func)
