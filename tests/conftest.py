import os
import pathlib

import pytest
import yaml
from perscache import Cache
from perscache.storage import LocalFileStorage

env = pathlib.Path(".env.yaml")
if env.exists():
    env_dict = yaml.safe_load(env.read_text())
    for key, value in env_dict.items():
        os.environ[key] = value


@pytest.fixture
def cache(tmp_path):
    return Cache(storage=LocalFileStorage(tmp_path))
