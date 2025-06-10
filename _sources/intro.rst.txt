Introduction
============

**PyESys** is a Python-native, thread-safe, type-safe event system designed to feel intuitive in real-world applications — especially those involving concurrency, simulation, or external control.

----

Why PyESys?
-----------

While Python lacks a built-in observer pattern, many third-party libraries exist — but most feel **foreign to the language**. They often:

- Depend on **string-based global keys** for event names
- Use **shared registries** that introduce tight coupling
- Are **awkward** to manage per-instance behaviour
- Handle **async vs sync inconsistently**
- Leak memory when managing bound methods
- Feel nothing like Python or .NET's event model

PyESys was born from practical needs:

> “I was modelling and controlling a plant in real time (in its own thread/process), and I wanted a clean way to control it via external events. The existing solutions felt clunky or unfamiliar.”

----

Goals
-----

- **Per-instance events** by default — no more global keys
- Seamless **sync + async** support (handlers, emitters)
- Automatic **weak-reference clean-up** for bound methods
- Familiar model similar to **.NET events**
- Built to “just work” — no magic registries or ceremony
- Thread-safe emission and subscription
- Minimal memory management burden

----

Use Cases
---------

- Controlling long-running simulations from a UI or script
- Reacting to real-time data (sensor inputs, model outputs)
- Building testable, decoupled modules
- Replacing `Observer`/`Signal` constructs in Pythonic codebases
- Integrating `.NET-style` event patterns in scientific and industrial tooling

----

Design Philosophy
-----------------

- **Explicit signatures** — handler arity is enforced by example
- **Clean semantics** — events feel like properties with `+=` and `-=` syntax
- **Thread & coroutine friendly** — safe in all contexts
- **Composable and modular** — no central broker required
