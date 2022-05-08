from pathlib import Path

from perscache import Cache
from perscache.storage import LocalFileStorage


def test_max_size(tmp_path):
    MAX_SIZE = 10_000

    path: Path = tmp_path

    # path should be empty
    # assert path.stat().st_size == 0



    cache = Cache(storage=LocalFileStorage(path, max_size=MAX_SIZE))

    counter = 0

    @cache.cache()
    def get_data(key):
        nonlocal counter
        counter += 1
        return [counter] * 5000

    get_data(1)
    get_data(2)
    get_data(3)
    get_data(4)

    assert path.stat().st_size <= MAX_SIZE

    assert counter == 4
