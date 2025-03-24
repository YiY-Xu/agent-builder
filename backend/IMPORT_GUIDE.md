# Backend Python Import Structure

## Overview

This guide explains the proper way to structure imports in the backend Python code for AgentStudio.

## Import Best Practices

### 1. Always Use Absolute Imports

All imports in the project should use absolute imports starting with `app`. For example:

```python
# ✅ Correct
from app.config.settings import settings
from app.services.knowledge_service import KnowledgeService

# ❌ Incorrect - Do not use relative imports
from ..config.settings import settings
from .knowledge_service import KnowledgeService
```

### 2. Python Package Structure

The app is structured as a proper Python package:

```
agent-builder/
└── backend/
    └── app/
        ├── __init__.py
        ├── main.py
        ├── config/
        ├── models/
        ├── routers/
        ├── services/
        └── tests/
```

### 3. Running Tests

When running tests, ensure you're in the correct directory:

```bash
# Run from the backend directory, not from inside app
cd agent-builder/backend
python -m pytest app/tests
```

For running individual test files:

```bash
python -m pytest app/tests/test_knowledge_service.py -v
```

### 4. Common Import Problems

If you encounter import errors like:
- `ImportError: attempted relative import beyond top-level package`
- `ModuleNotFoundError: No module named 'app'`

Try the following:
1. Make sure all imports use the absolute `app.*` format
2. Run pytest from the correct directory (backend, not app)
3. If needed, add this to the test file to modify the Python path:
   ```python
   import sys
   import os
   sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
   ```

### 5. Testing Imports

If you need to mock imports in tests, use the correct absolute path:

```python
# ✅ Correct
with patch('app.services.knowledge_service.settings', MockSettings()):
    yield

# ❌ Incorrect
with patch('services.knowledge_service.settings', MockSettings()):
    yield
```

## Examples

### Router Import Example
```python
# app/routers/knowledge.py
from fastapi import APIRouter, Depends
from app.services.knowledge_service import KnowledgeService
```

### Service Import Example
```python
# app/services/knowledge_service.py
from app.config.settings import settings
from app.models.request_models import SomeModel
```

### Tests Import Example
```python
# app/tests/test_service.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from app.services.some_service import SomeService
```
