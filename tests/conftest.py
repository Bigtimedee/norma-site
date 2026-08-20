import sys
from pathlib import Path

# Allow test files to import directly from agent/ (e.g. `from content_generator import ...`)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))
