import os
import sys

# Ensure backend directory is at the top of sys.path so backend modules load under one canonical namespace
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from main import app
