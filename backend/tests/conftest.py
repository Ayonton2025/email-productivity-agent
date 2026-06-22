import sys
import os
# Ensure backend package is on sys.path for pytest
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Expose environment variable to point at backend for imports
os.environ.setdefault('PYTHONPATH', ROOT)
