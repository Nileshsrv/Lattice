import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = Path(os.environ.get("LATTICE_DATA_DIR", REPO_ROOT / "var"))
OBJECTS_DIR = DATA_DIR / "objects"
DB_PATH = DATA_DIR / "lattice.db"

SAMPLE_DATA_DIR = REPO_ROOT / "sample_data"

# MVP policy ceilings (architecture.md §8.2)
MAX_UPLOAD_BYTES = 100 * 1024 * 1024
MAX_PROJECT_BYTES = 1024 * 1024 * 1024

SESSION_TTL_HOURS = 24 * 14

# Run execution limits (DR-4): wall-clock per category, RSS cap enforced by a
# watchdog that polls the worker process (works on Windows, unlike rlimits).
RUN_TIMEOUT_SECONDS = {"instant": 20, "long-running": 180}
RUN_MEMORY_LIMIT_MB = int(os.environ.get("LATTICE_RUN_MEMORY_LIMIT_MB", "1536"))


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OBJECTS_DIR.mkdir(parents=True, exist_ok=True)


def db_url() -> str:
    return f"sqlite:///{DB_PATH}"
