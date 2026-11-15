import os
import sys
import tempfile
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

# Must be set before any lattice import so DB and object store land in a
# throwaway directory, never in the developer's var/.
os.environ.setdefault("LATTICE_DATA_DIR", tempfile.mkdtemp(prefix="lattice-test-"))
