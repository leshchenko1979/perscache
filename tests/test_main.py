import datetime as dt

import pytest
from beartype.roar import BeartypeCallHintParamViolation
from icontract import ViolationError
from perscache import Cache
from perscache.cache import NoCache


def test_repr(cache):
    assert "CloudPickleSerializer" in repr(cache.serializer)
    assert "LocalFileStorage" in repr(cache.storage)
    assert "Cache" in repr(cache)
    assert "NoCache" in repr(NoCache())


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


def test_typing(cache):
    with pytest.raises(BeartypeCallHintParamViolation):
        Cache("asd")

    with pytest.raises(BeartypeCallHintParamViolation):

        @cache(ttl=10)
        def get_data():
            ...

    with pytest.raises(ViolationError):

        @cache(ignore=["abc"])
        def get_data():
            ...

    with pytest.raises(ViolationError):

        @cache(ttl=dt.timedelta(days=-1))
        def get_data():
            ...
