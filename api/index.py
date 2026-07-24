import os
import sys

# Add backend directory to sys.path so imports inside backend work
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from backend.main import app
