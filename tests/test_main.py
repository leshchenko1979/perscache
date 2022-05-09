import pytest
from perscache import Cache
from perscache.cache import NoCache
from perscache.serializers import (
    CloudPickleSerializer,
    JSONSerializer,
    PickleSerializer,
)
from perscache.storage import LocalFileStorage


@pytest.fixture
def cache(tmp_path):
    return Cache(storage=LocalFileStorage(tmp_path))


def test_repr(cache):
    assert "CloudPickleSerializer" in repr(cache.serializer)
    assert "LocalFileStorage" in repr(cache.storage)
    assert "Cache" in repr(cache)


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


def test_alias(cache):

    counter = 0

    @cache.cache()
    def get_data():
        nonlocal counter
        counter += 1
        return "abc"

    get_data()
    get_data()

    assert counter == 1


def test_no_parens(cache):

    counter = 0

    @cache
    def get_data():
        nonlocal counter
        counter += 1
        return "abc"

    get_data()
    get_data()

    assert counter == 1


@pytest.mark.asyncio
async def test_basic_async(cache):

    counter = 0

    @cache()
    async def get_data():
        nonlocal counter
        counter += 1
        return "abc"

    await get_data()
    await get_data()

    assert counter == 1


def test_arg_change(cache):

    global_key = None

    @cache()
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
    @cache()
    def get_data(key):
        return key

    hash1 = cache._get_key(get_data, None, None, None, None)

    @cache()
    def get_data(key):
        print("This function has been changed...")
        return key

    hash2 = cache._get_key(get_data, None, None, None, None)

    assert hash1 != hash2


def test_serializer_change(cache: Cache):

    counter = 0

    @cache(serializer=PickleSerializer())
    def get_data():
        nonlocal counter
        counter += 1
        return "abc"

    get_data()

    # now, let's change the serializer

    @cache(serializer=JSONSerializer())
    def get_data():
        nonlocal counter
        counter += 1
        return "abc"

    get_data()  # cache invalidated, the function should be called again

    assert counter == 2


def test_ignore_args(cache):

    counter = 0

    @cache(ignore=["ignore_this"])
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

    @cache()
    def get_data():
        nonlocal counter
        counter += 1
        return "abc"

    get_data()
    get_data()

    assert counter == 2


def data():
    SIZE = 100_000

    # long string
    data1 = ["A"] * SIZE
    data2 = data1.copy()
    data2[SIZE // 2] = ["B"]

    yield data1, data2

    # long list
    data1 = "A" * SIZE
    middle = SIZE // 2
    data2 = f"{data1[:middle]}B{data1[middle:]}"

    yield data1, data2

    # object with no repr() function
    class Data:
        pass

    data1, data2 = Data(), Data()
    data1.a = 1
    data2.b = 2

    # object with a non-changing repr()
    class Data:
        def __repr__(self):
            return "This never changes"

    data1, data2 = Data(), Data()
    data1.a = 1
    data2.b = 2

    yield data1, data2


def test_hash(tmp_path):
    cache = Cache(
        serializer=CloudPickleSerializer(), storage=LocalFileStorage(tmp_path)
    )
    for data1, data2 in data():
        assert data1 != data2
        assert cache._get_key(
            lambda: None, (data1,), None, CloudPickleSerializer(), None
        ) != cache._get_key(lambda: None, (data2,), None, CloudPickleSerializer(), None)
