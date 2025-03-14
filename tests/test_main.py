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
        def get_data(): ...

    with pytest.raises(ViolationError):

        @cache(ignore=["abc"])
        def get_data(): ...

    with pytest.raises(ViolationError):

        @cache(ttl=dt.timedelta(days=-1))
        def get_data(): ...


def test_class_method_with_params(cache):
    from datetime import datetime, timedelta, timezone
    from pathlib import Path
    from perscache import Cache
    from perscache.storage import LocalFileStorage

    cache = Cache(storage=LocalFileStorage(Path.home().joinpath(".cache/test")))

    class PerscacheTest:
        @cache(ttl=timedelta(hours=1))
        def cache_method(self, what: str, when: datetime):
            return f"What: {what}, Timestamp: {when.isoformat()}"

    pt = PerscacheTest()
    pt.cache_method("This thing happened", datetime.now(tz=timezone.utc))


def test_sync_class_method(cache):
    """Test that sync class methods work correctly with caching."""

    class Calculator:
        def __init__(self):
            self.compute_count = 0

        @cache
        def add(self, a: int, b: int) -> int:
            self.compute_count += 1
            return a + b

    calc = Calculator()

    # First call should compute
    result1 = calc.add(5, 3)
    assert result1 == 8
    assert calc.compute_count == 1

    # Second call should use cache
    result2 = calc.add(5, 3)
    assert result2 == 8
    assert calc.compute_count == 1  # Count shouldn't increase


def test_sync_class_method_multiple_instances(cache):
    """Test that caches for different instances of the same class don't clash."""

    class Counter:
        def __init__(self, id: str):
            self.id = id
            self.compute_count = 0

        @cache
        def increment(self, n: int) -> int:
            self.compute_count += 1
            return n + 1

    counter1 = Counter("first")
    counter2 = Counter("second")

    # First instance first call
    result1 = counter1.increment(5)
    assert result1 == 6
    assert counter1.compute_count == 1
    assert counter2.compute_count == 0

    # Second instance first call with same input
    result2 = counter2.increment(5)
    assert result2 == 6
    assert counter1.compute_count == 1
    assert counter2.compute_count == 1  # Should compute for second instance

    # First instance second call
    result3 = counter1.increment(5)
    assert result3 == 6
    assert counter1.compute_count == 1  # Should use cache
    assert counter2.compute_count == 1

    # Second instance second call
    result4 = counter2.increment(5)
    assert result4 == 6
    assert counter1.compute_count == 1
    assert counter2.compute_count == 1  # Should use cache


def test_async_class_method(cache):
    """Test that async class methods work correctly with caching."""
    import asyncio

    class AsyncCalculator:
        def __init__(self):
            self.compute_count = 0

        @cache
        async def multiply(self, a: int, b: int) -> int:
            self.compute_count += 1
            await asyncio.sleep(0.1)  # Simulate async work
            return a * b

    async def run_test():
        calc = AsyncCalculator()

        # First call should compute
        result1 = await calc.multiply(4, 3)
        assert result1 == 12
        assert calc.compute_count == 1

        # Second call should use cache
        result2 = await calc.multiply(4, 3)
        assert result2 == 12
        assert calc.compute_count == 1  # Count shouldn't increase

    asyncio.run(run_test())


def test_async_class_method_multiple_instances(cache):
    """Test that caches for different async instances of the same class don't clash."""
    import asyncio

    class AsyncProcessor:
        def __init__(self, id: str):
            self.id = id
            self.compute_count = 0

        @cache
        async def process(self, data: str) -> str:
            self.compute_count += 1
            await asyncio.sleep(0.1)  # Simulate async work
            return f"{self.id}:{data}"

    async def run_test():
        proc1 = AsyncProcessor("A")
        proc2 = AsyncProcessor("B")

        # First instance first call
        result1 = await proc1.process("test")
        assert result1 == "A:test"
        assert proc1.compute_count == 1
        assert proc2.compute_count == 0

        # Second instance first call with same input
        result2 = await proc2.process("test")
        assert result2 == "B:test"  # Different result due to different instance
        assert proc1.compute_count == 1
        assert proc2.compute_count == 1  # Should compute for second instance

        # First instance second call
        result3 = await proc1.process("test")
        assert result3 == "A:test"
        assert proc1.compute_count == 1  # Should use cache
        assert proc2.compute_count == 1

        # Second instance second call
        result4 = await proc2.process("test")
        assert result4 == "B:test"
        assert proc1.compute_count == 1
        assert proc2.compute_count == 1  # Should use cache

    asyncio.run(run_test())
