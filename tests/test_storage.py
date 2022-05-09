from pathlib import Path

import pytest

from perscache import Cache
from perscache.storage import LocalFileStorage


@pytest.mark.parametrize("max_size", [0, 1000, 10_000])
def test_max_size(tmp_path, max_size):
    path: Path = tmp_path

    cache = Cache(storage=LocalFileStorage(path, max_size=max_size))

    initial_size = path.stat().st_size
    counter = 0

    @cache()
    def get_data(key):
        nonlocal counter
        counter += 1
        return [counter] * min((max_size // 2), 100)

    get_data(1)
    get_data(2)
    get_data(3)
    get_data(4)

    assert path.stat().st_size <= max(max_size, initial_size)

    assert counter == 4

def test_no_path(tmp_path):
    path: Path = tmp_path / "new_path"
    assert not path.exists()

    cache = Cache(storage=LocalFileStorage(path))
    cache._set("a", 1, cache.serializer, cache.storage)

    assert path.exists()
