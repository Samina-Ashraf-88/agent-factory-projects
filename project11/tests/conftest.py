import csv
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.importer import import_wallet  # noqa: E402
from src.main import analyze  # noqa: E402
from src.normalizer import normalize  # noqa: E402

SAMPLE = ROOT / "data" / "sample_wallet.csv"


@pytest.fixture(scope="session")
def sample_results():
    return analyze(import_wallet([SAMPLE]), opening_balance=6000)


@pytest.fixture
def make_csv(tmp_path):
    def _make(rows, name="wallet.csv", header=("Date", "Time", "Description", "Amount")):
        path = tmp_path / name
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(header)
            writer.writerows(rows)
        return path
    return _make


@pytest.fixture
def frame_of(make_csv):
    """Normalized DataFrame from (date, time, description, amount) rows."""
    def _frame(rows):
        return normalize(import_wallet([make_csv(rows)]).frame)
    return _frame
