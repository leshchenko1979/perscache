import pytest
from perscache import Cache
from perscache.storage import LocalFileStorage


@pytest.fixture
def cache(tmp_path):
    return Cache(storage=LocalFileStorage(tmp_path))
