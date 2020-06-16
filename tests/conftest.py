import os
from pathlib import Path

import pytest

CURRENT_DIR = Path(os.path.dirname(os.path.realpath(__file__)))
PROJECT_DIR = CURRENT_DIR.parent
TEST_DATA_DIR = CURRENT_DIR / "test_hist_data"


@pytest.fixture(scope="module")
def test_count():
    tests_ran = 0
    return tests_ran
