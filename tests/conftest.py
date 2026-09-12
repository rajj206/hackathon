import os
import shutil
import uuid
from pathlib import Path

import pytest

os.environ["EXTRACTOR_PROVIDER"] = "heuristic"
os.environ["CHAT_PROVIDER"] = "local"
os.environ["TRANSCRIPTION_PROVIDER"] = "local"
os.environ["WAR_ROOM_PROVIDER"] = "disabled"


@pytest.fixture
def runtime_dir():
    path = Path(".test-data") / str(uuid.uuid4())
    path.mkdir(parents=True)
    yield path
    shutil.rmtree(path, ignore_errors=True)
