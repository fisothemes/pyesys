# Contributing to PyESys

Thank you for your interest in contributing to **PyESys**, a thread-safe, type-safe Python event system with async support. This guide explains our workflow, coding conventions, and how to get your changes merged efficiently.


## Table of Contents

1. [Getting Started](#getting-started)  
   - [Fork and Clone](#fork-and-clone)  
   - [Setting Up](#setting-up)  
2. [Branching & Workflow](#branching--workflow)  
   - [Feature Branches](#feature-branches)  
   - [Bug Fixes](#bug-fixes)  
   - [Chores & Documentation](#chores--documentation)  
   - [Hotfixes](#hotfixes)  
3. [Coding Conventions](#coding-conventions)  
   - [Project Layout](#project-layout)  
   - [Styling & Formatting](#styling--formatting)  
   - [Type Annotations](#type-annotations)  
   - [Docstrings](#docstrings)  
   - [Error Handling](#error-handling)  
4. [Testing](#testing)  
   - [Running Tests](#running-tests)  
   - [Writing New Tests](#writing-new-tests)  
5. [Pull Request Process](#pull-request-process)  
   - [Keeping Your Fork Up to Date](#keeping-your-fork-up-to-date)  
   - [Creating a Pull Request](#creating-a-pull-request)  
6. [Attribution & License](#attribution--license)  


## Getting Started

### Fork and Clone

1. **Fork** the repository on GitHub:
   [https://github.com/fisothemes/pyesys](https://github.com/fisothemes/pyesys)

2. **Clone** your fork to your local machine:
   ```bash
   git clone https://github.com/<your-username>/pyesys.git
   cd pyesys
    ```

3. **Add upstream remote** to keep in sync:

   ```bash
   git remote add upstream https://github.com/fisothemes/pyesys.git
   git fetch upstream
   ```

### Setting Up

1. **Install the package in editable mode** (so changes to `src/pyesys` are reflected immediately):

   ```bash
   pip install -e .[test]
   ```

   This installs PyESys itself plus the `[test]` extras (`pytest`, `pytest-asyncio`).

2. **Verify your environment**:

   ```bash
   pytest -q
   ```

   All tests should pass before you begin making changes.

---

## Branching & Workflow

We follow a simple Git-Flow–inspired model:

1. **`master`** branch holds release-ready code (matching the latest PyPI version).
2. **`develop`** branch is where ongoing work is staged. New features and fixes are merged here first.

### Feature Branches

* Base your branch off of `develop`.

* Name it with the prefix `feature/`, e.g.:

  ```bash
  git checkout develop
  git pull upstream develop
  git checkout -b feature/my-new-event-method
  ```

* Commit often, with clear messages (see [Commit Messages](#commit-messages) below).

* When complete, merge into `develop` via a Pull Request.

### Bug Fixes

* Base your branch off of `develop`.
* Use the prefix `fix/`, e.g.:

  ```bash
  git checkout develop
  git pull upstream develop
  git checkout -b fix/cleanup-edge-case
  ```
* After testing, submit a PR to `develop`.

### Chores & Documentation

* Non–user-facing changes (e.g. refactoring, updating docs, bumping version) go on `chore/…`:

  ```bash
  git checkout develop
  git pull upstream develop
  git checkout -b chore/update-readme
  ```
* Merge into `develop` via PR when ready.

### Hotfixes

* For urgent fixes that must go directly into `master` (e.g. production‐blocking bugs), branch from `master`:

  ```bash
  git checkout main
  git pull upstream main
  git checkout -b hotfix/critical-fix
  ```
* After fixing, create a PR targeting `master`. Once merged, cherry‐pick or merge into `develop` too.


## Coding Conventions

### Project Layout

```
pyesys/                          ← repo root
├── .github/                    ← GitHub Actions workflows & templates
├── pyproject.toml              ← Metadata & build configuration
├── README.md
├── LICENSE
├── docs/                       ← Documentation source files
├── examples/                   ← Example scripts
├── tools/                      ← Utility scripts
├── src/                        ← Source code (src-layout)
│   └── pyesys/
│       ├── __init__.py
│       ├── handler.py
│       ├── event.py
│       └── utils.py            ← utility functions and helpers
└── tests/                      ← Test suite
   ├── __init__.py
   ├── integration/            ← Integration tests
   │   └── ...
   └── unit/                   ← Unit tests
       └── ...
```

### Styling & Formatting

* Follow **PEP 8** for code style.
* Use **4 spaces** for indentation (no tabs).
* Keep lines ≤ 88 characters to work well with common linters/formatters.
* We recommend using **Black** to auto‐format:

  ```bash
  pip install black
  black src/pyesys tests
  ```

### Type Annotations

* All public functions and methods should include **type hints**.
* Use `ParamSpec` and `Generic` for event handler signatures.
* Example:

  ```python
  from typing import Callable, Optional, Protocol, ParamSpec

  P = ParamSpec("P")

  class ErrorHandler(Protocol):
      def __call__(self, exception: Exception, handler: Callable[..., None]) -> None: ...
  ```

### Docstrings

* Use **Google-style** or **PEP 257** docstrings for all public classes/methods.
* Include a **one-line summary**, followed by a blank line and detailed description if needed.
* Example:

  ```python
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
  ```

### Error Handling

* **Isolate exceptions** in callbacks: individual handler errors should not stop other handlers.
* Route exceptions to the configured `error_handler` (default prints to `stderr`).
* When raising `TypeError` for signature mismatches, include a clear message.


## Testing

### Running Tests

Ensure dev-dependencies are installed:

```bash
pip install -e .[dev]
```

Then simply run:

```bash
pytest -q
```

This runs both `test_handler.py` and `test_event.py`. All tests must pass before opening a PR.

### Writing New Tests

* Place test files under `tests/`, named `test_*.py`.
* Use **pytest fixtures** sparingly; most tests can use plain functions with `assert`.
* For async tests, mark with `@pytest.mark.asyncio` and declare `async def`:

  ```python
  import pytest

  @pytest.mark.asyncio
  async def test_emit_async():
      results = []
      async def ah(x: int) -> None:
          results.append(x)

      event, listener = create_event(example=lambda x: None)
      listener += ah

      await event.emit_async(5)
      assert results == [5]
  ```
* Cover edge cases:

  * Signature mismatches (`TypeError`)
  * Weak‐ref cleanup
  * Duplicate vs. non-duplicate behaviour
  * Custom `error_handler` routing
  * `handler_count` and `handlers` introspection

---

## Pull Request Process

### Keeping Your Fork Up to Date

Before starting new work or submitting a PR:

```bash
git checkout develop
git fetch upstream
git merge upstream/develop
```

Resolve any merge conflicts locally, then push `develop` to your fork:

```bash
git push origin develop
```

### Creating a Pull Request

1. **Push** your feature/fix branch to your fork:

   ```bash
   git push origin <your-branch-name>
   ```
2. Go to the original repo on GitHub:
   [https://github.com/fisothemes/pyesys](https://github.com/fisothemes/pyesys)
3. Click **“Compare & pull request.”**
4. **Title & description**: Explain what changed, why it’s needed, and reference any related issues (e.g. “Closes #12”).
5. **Target branch**:

   * For new features or fixes, target `develop`.
   * For urgent hotfixes, target `master`.
6. Submit the PR. CI (via GitHub Actions) will run tests automatically.

## Attribution & License

PyESys is released under the **MIT License**. See [LICENSE](LICENSE) for details.

This CONTRIBUTING guide is adapted for PyESys to help streamline contributions and maintain consistent code quality. If you have any questions, feel free to open an issue or start a discussion.

Thank you for helping make PyESys better!