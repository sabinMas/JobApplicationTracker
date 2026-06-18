# Ruff Linting & Formatting Guide

This guide covers Ruff usage for the JobApplicationTracker backend. Ruff catches code quality, style, and formatting issues before CI/CD.

## Quick Start

Run these before committing:

```bash
cd backend

# Check for linting errors (F, E)
ruff check app/

# Fix linting errors automatically
ruff check app/ --fix

# Fix unsafe linting errors (use with caution)
ruff check app/ --fix --unsafe-fixes

# Format code (auto-fix style issues)
ruff format app/

# Format check without modifying (CI mode)
ruff format --check app/
```

## Common Ruff Errors

### F: PyFlakes — Code Correctness

| Error | Cause | Fix |
|-------|-------|-----|
| **F401** | Unused import | Remove the import or use it. Check `import X` at top but never referenced |
| **F841** | Unused variable | Remove assignment or use the variable (`_ = var` to suppress if intentional) |
| **F811** | Redefined name | Variable defined twice in same scope; rename one |
| **F821** | Undefined name | Typo in variable name or forgot to import it |
| **F631** | Assertion test is a tuple | Change `assert (x, y)` to `assert (x, y) != ()` or use `assert x and y` |

**Examples:**
```python
# ❌ F401: Unused import
import os  # Never used

# ✅ Fix: Remove it
# (no import)

# ❌ F841: Unused variable
def process(data):
    result = expensive_calc(data)  # Never used!
    return "done"

# ✅ Fix: Remove or use it
def process(data):
    result = expensive_calc(data)
    return result

# ❌ F811: Redefined name
x = 10
x = 20  # OK, but watch for shadowing function names
def should_retry(error):
    should_retry, wait = check_retry(error)  # ⚠️ Shadows function name!
    return should_retry

# ✅ Fix: Rename variable
def should_retry(error):
    should_retry_flag, wait = check_retry(error)
    return should_retry_flag
```

### E: Errors — Syntax & Formatting

| Error | Cause | Fix |
|-------|-------|-----|
| **E501** | Line too long (>88 chars) | Break into multiple lines or use implicit line continuation |
| **E261** | Multiple spaces before inline comment | Use one space before `#` |
| **E302** | Expected 2 blank lines, found N | Add blank lines between function definitions |

**Examples:**
```python
# ❌ E501: Line too long
def my_function(very_long_arg1, very_long_arg2, very_long_arg3, very_long_arg4):

# ✅ Fix: Break into multiple lines
def my_function(
    very_long_arg1,
    very_long_arg2,
    very_long_arg3,
    very_long_arg4,
):
```

### W: Warnings — Style Issues

| Error | Cause | Fix |
|-------|-------|-----|
| **W292** | No newline at end of file | Add newline to EOF |
| **W605** | Invalid escape sequence | Use raw string `r"..."` or escape properly |

## Code Style Conventions

### Imports
```python
# ✅ Correct order:
# 1. Standard library
import os
import asyncio
from datetime import datetime

# 2. Third-party
import httpx
from sqlalchemy import select

# 3. Local
from ..models import Job
from ..logging_config import get_logger

# ❌ Wrong: Mixed order or duplicates
from datetime import datetime
import os  # After third-party!
```

### Async/Await
```python
# ✅ Correct: All I/O is async
async def get_data():
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
    return resp.json()

# ❌ Wrong: Synchronous I/O
def get_data():
    import requests  # Synchronous!
    resp = requests.get(url)
    return resp.json()

# ❌ Wrong: Unused async
async def process():
    data = get_sync_data()  # Not awaited, not a coroutine
    return data
```

### Type Hints
```python
# ✅ Correct: All functions have type hints
async def merge_profiles(
    existing: Profile,
    extracted: dict,
) -> tuple[Profile, list[str]]:
    ...

# ❌ Wrong: Missing return type or arg types
async def merge_profiles(existing, extracted):
    ...
```

### Exception Handling
```python
# ✅ Correct: Specific exception
try:
    data = await client.get(url)
except asyncio.TimeoutError:
    logger.warning("Timeout")

# ❌ Wrong: Bare except
try:
    data = await client.get(url)
except:  # ← Catches KeyboardInterrupt too!
    pass

# ✅ Also correct: Explicit Exception
try:
    data = await client.get(url)
except Exception:
    logger.error("Failed")
```

### F-Strings
```python
# ✅ Correct: Only use f-string if there's a placeholder
message = f"User {name} created"

# ❌ Wrong: No placeholders (unnecessary f-prefix)
message = f"Job application submitted"  # Should be "Job application submitted"

# ✅ Correct: Placeholder
message = f"Job {job_id} discovered"
```

### Logging
```python
# ✅ Correct: Use structured logger
from ..logging_config import get_logger
logger = get_logger(__name__)

logger.info("Job synced", extra_fields={"job_id": 123})

# ❌ Wrong: Using print
print("Job synced")  # Not logged to CloudWatch

# ❌ Wrong: f-string without context fields
logger.info(f"Synced {job_id} jobs")  # OK but not structured
```

## Pre-Commit Checklist

Before `git commit`, run:

```bash
# 1. Lint check
ruff check app/ --fix

# 2. Format check
ruff format app/

# 3. Run tests
pytest tests/ -x -v

# 4. Verify no other linting tools complain
# (pytest, mypy, etc.)
```

If any step fails, fix and re-run before committing.

## CI/CD Integration

The GitHub Actions pipeline runs:

```bash
ruff check app/          # Must pass
ruff format --check app/ # Must pass
pytest tests/            # Must pass
```

All three must succeed before merge.

## GitHub Actions Workflow

When you push, the `backend-lint` job runs:

1. **Lint check** — `ruff check app/` (F, E rules)
2. **Format check** — `ruff format --check app/` (Black-compatible formatting)
3. **Test** — `pytest tests/` (Unit tests)

**If any fail:**
- Pull CI logs and read the error
- Fix locally: `ruff check app/ --fix && ruff format app/`
- Run tests: `pytest tests/`
- Commit and push

## Most Common Mistakes

1. **Unused imports** — Remove dead imports. Check `from X import Y` but Y is never used.
2. **Unused variables** — Don't assign if you won't use. Or use `_` prefix to suppress.
3. **Async mistakes** — All DB/HTTP calls must be `await`ed. Use AsyncSession, httpx.AsyncClient.
4. **Bare except** — Change `except:` to `except Exception:` to avoid catching KeyboardInterrupt.
5. **f-string without placeholder** — `f"text"` should be `"text"`.
6. **Line too long** — Break at 88 chars (Black default). Use implicit continuation.
7. **Variable shadowing** — Don't use same name for variable as enclosing function/class.

## Fixing Ruff Errors Locally

```bash
# Auto-fix most issues
cd backend
ruff check app/ --fix
ruff format app/

# Verify fixes worked
ruff check app/
ruff format --check app/

# Run tests to make sure nothing broke
pytest tests/ -x -v

# Commit if clean
git add -A
git commit -m "fix: resolve linting errors"
```

## References

- [Ruff Rules Reference](https://docs.astral.sh/ruff/rules/)
- [Black Code Style](https://black.readthedocs.io/en/stable/the_code_style.html)
- [PEP 8](https://pep8.org/)
- [PEP 257 (Docstrings)](https://pep257.dev/)
