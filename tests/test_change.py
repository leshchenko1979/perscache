import inspect

import pytest
from perscache import Cache
from perscache.serializers import (
    CloudPickleSerializer,
    JSONSerializer,
    PickleSerializer,
    make_serializer,
)
from perscache.storage import LocalFileStorage


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

    hash1 = cache._get_hash(get_data, (None,), {}, None, None)

    @cache()
    def get_data(key):
        print("This function has been changed...")
        return key

    hash2 = cache._get_hash(get_data, (None,), {}, None, None)

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

    @cache(ignore="ignore_this")
    def get_data(key, ignore_this):
        nonlocal counter
        counter += 1
        return key

    get_data("abc", ignore_this="ignore_1")
    assert counter == 1

    # using the cache although the `ignore_this` arg has changed
    get_data("abc", ignore_this="ignore_2")
    assert counter == 1


def test_ignore_positional_args(cache):

    counter = 0

    @cache(ignore="ignore_this")
    def get_data(key, ignore_this):
        nonlocal counter
        counter += 1
        return key

    get_data("abc", "ignore_1")
    assert counter == 1

    # using the cache although the `ignore_this` arg has changed
    get_data("abc", "ignore_2")
    assert counter == 1


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
        assert cache._get_hash(
            lambda x: None, (data1,), {}, CloudPickleSerializer(), None
        ) != cache._get_hash(
            lambda x: None, (data2,), {}, CloudPickleSerializer(), None
        )


@pytest.mark.asyncio
async def test_retrieve_with_new_cache(tmp_path):
    counter = 0

    cache = Cache(storage=LocalFileStorage(tmp_path))

    @cache(ignore={"app", "key"})
    async def get_data(app, key):
        nonlocal counter
        counter += 1
        return "abc"

    source1 = inspect.getsource(get_data)

    assert await get_data("xxx", 111) == "abc"
    assert counter == 1

    # and now, a new cache...
    cache = Cache(storage=LocalFileStorage(tmp_path))

    # ...for the same function
    @cache(ignore={"app", "key"})
    async def get_data(app, key):
        nonlocal counter
        counter += 1
        return "abc"

    source2 = inspect.getsource(get_data)

    assert source1 == source2  # source same

    # should be taken from cache
    assert await get_data("yyy", 222) == "abc"
    assert counter == 1


@pytest.mark.xfail(
    reason=(
        "There is no way to understand if the implementation of the serializer has changed"
        " if it was created with make_serializer()"
    )
)
def test_retrieve_with_new_serializer(cache):
    counter = 0

    @cache(ignore={"app", "key"})
    def get_data(app, key):
        nonlocal counter
        counter += 1
        return "abc"

    DummySerializer = make_serializer(
        "DummySerializer", "dummy", lambda x: x, lambda x: x
    )
    source1 = inspect.getsource(cache.serializer.dumps)

    assert get_data("xxx", 111) == "abc"
    assert counter == 1

    # and now, a new serializer...
    DummySerializer = make_serializer(
        "DummySerializer", "dummy", lambda x: x * 2, lambda x: x * 2
    )

    source2 = inspect.getsource(cache.serializer.dumps)

    assert source1 != source2  # source not the same

    get_data("yyy", 222)

    # should NOT be taken from cache
    assert counter == 2


def test_make_serializer():
    DummySerializer = make_serializer(
        "DummySerializer", "dummy", lambda x: x, lambda x: x
    )
    assert DummySerializer.__name__ == "DummySerializer"  # important for hashing
