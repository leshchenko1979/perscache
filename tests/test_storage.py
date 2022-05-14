import datetime as dt
import os
import time
from pathlib import Path

import pytest
from perscache import Cache
from perscache.storage import GoogleCloudStorage, LocalFileStorage

caches = ["local"]

if os.environ.get("GOOGLE_TOKEN") and os.environ.get("GOOGLE_BUCKET"):
    caches.append("gcs")


@pytest.fixture(params=caches)
def cache(request):
    if request.param == "local":
        storage = LocalFileStorage(Path("/tmp/perscache_test_cache"))
    elif request.param == "gcs":
        storage = GoogleCloudStorage(
            Path(os.environ["GOOGLE_BUCKET"]) / "perscache_test_cache",
            storage_options={"token": os.environ["GOOGLE_TOKEN"]},
        )
    yield Cache(storage=storage)
    storage.clear()


def test_basic(cache):

    counter = 0

    @cache()
    def get_data():
        nonlocal counter
        counter += 1
        return "abc"

    get_data()
    get_data()

    assert counter == 1


@pytest.mark.parametrize("max_size", [0, 1000, 10_000])
def test_max_size(cache, max_size):
    path: Path = cache.storage.location

    cache.storage.max_size = max_size

    cache.storage.ensure_path(path)
    initial_size = cache.storage.size(path)

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

    assert cache.storage.size(path) <= max(max_size, initial_size)

    assert counter == 4


def test_ttl(cache):
    counter = 0

    if isinstance(cache.storage, LocalFileStorage):
        ttl_sec, delay = 0.1, 0.2
    else:
        ttl_sec, delay = 3, 5  # setting safe timeouts for GCS

    @cache(ttl=dt.timedelta(seconds=ttl_sec))
    def get_data(key):
        nonlocal counter
        counter += 1
        return key

    get_data(1)
    assert counter == 1

    get_data(1)
    assert counter == 1

    get_data(2)
    assert counter == 2

    time.sleep(delay)

    get_data(1)
    assert counter == 3

    get_data(2)
    assert counter == 4


def test_initialization():
    LocalFileStorage()
    GoogleCloudStorage()
