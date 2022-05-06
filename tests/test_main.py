import pytest
from perscache import Cache
from perscache.cache import NoCache
from perscache.serializers import JSONSerializer, PickleSerializer
from perscache.storage import LocalFileStorage


@pytest.fixture
def cache(tmp_path):
    return Cache(storage=LocalFileStorage(tmp_path))


def test_basic(cache):

    counter = 0

    @cache.cache()
    def get_data():
        nonlocal counter
        counter += 1
        return "abc"

    get_data()
    get_data()

    assert counter == 1


def test_arg_change(cache):

    global_key = None

    @cache.cache()
    def get_data(key):
        nonlocal global_key
        global_key = key
        return key

    get_data("abc")
    assert global_key == "abc"

    get_data("fgh")  # the function has been called again
    assert global_key == "fgh"

    get_data("abc")  # using the cache
    assert global_key == "fgh"


def test_body_change(cache: Cache):
    @cache.cache()
    def get_data(key):
        return key

    hash1 = cache.get_key(get_data, None, None, None)

    @cache.cache()
    def get_data(key):
        print("This function has been changed...")
        return key

    hash2 = cache.get_key(get_data, None, None, None)

    assert hash1 != hash2


def test_serializer_change(cache: Cache):

    counter = 0

    @cache.cache(serializer=PickleSerializer())
    def get_data():
        nonlocal counter
        counter += 1
        return "abc"

    get_data()

    # now, let's change the serializer

    @cache.cache(serializer=JSONSerializer())
    def get_data():
        nonlocal counter
        counter += 1
        return "abc"

    get_data()  # cache invalidated, the function should be called again

    assert counter == 2


def test_ignore_args(cache):

    counter = 0

    @cache.cache(ignore=["ignore_this"])
    def get_data(key, ignore_this):
        nonlocal counter
        counter += 1
        return key

    get_data("abc", ignore_this="ignore_1")
    assert counter == 1

    # using the cache although the `ignore_this` arg has changed
    get_data("abc", ignore_this="ignore_2")
    assert counter == 1


def test_no_cache():
    counter = 0

    cache = NoCache()

    @cache.cache()
    def get_data():
        nonlocal counter
        counter += 1
        return "abc"

    get_data()
    get_data()

    assert counter == 2
