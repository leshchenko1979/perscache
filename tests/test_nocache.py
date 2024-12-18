from perscache import NoCache
import asyncio

def test_no_cache_with_parentheses():
    counter = 0
    cache = NoCache()
    @cache()
    def dummy_func():
        nonlocal counter
        counter += 1
        return 'NoCache with parentheses'

    assert dummy_func() == 'NoCache with parentheses'
    assert dummy_func() == 'NoCache with parentheses'
    assert counter == 2


def test_no_cache_without_parentheses():
    counter = 0
    cache = NoCache()

    @cache
    def dummy_func():
        nonlocal counter
        counter += 1
        return 'NoCache without parentheses'

    assert dummy_func() == 'NoCache without parentheses'
    assert dummy_func() == 'NoCache without parentheses'
    assert counter == 2


async def test_no_cache_with_parentheses_async():
    counter = 0
    cache = NoCache()

    @cache()
    async def dummy_func():
        nonlocal counter
        counter += 1
        return 'NoCache with parentheses async'

    assert await dummy_func() == 'NoCache with parentheses async'
    assert await dummy_func() == 'NoCache with parentheses async'
    assert counter == 2


async def test_no_cache_without_parentheses_async():
    counter = 0
    cache = NoCache()

    @cache
    async def dummy_func():
        nonlocal counter
        counter += 1
        return 'NoCache without parentheses async'

    assert await dummy_func() == 'NoCache without parentheses async'
    assert await dummy_func() == 'NoCache without parentheses async'
    assert counter == 2


def test_no_cache_instance_method():
    cache = NoCache()

    class Calculator:
        def __init__(self):
            self.compute_count = 0

        @cache
        def add(self, a: int, b: int) -> int:
            self.compute_count += 1
            return a + b

    calc1 = Calculator()
    calc2 = Calculator()

    # First instance calls
    assert calc1.add(5, 3) == 8
    assert calc1.add(5, 3) == 8  # Should call again
    assert calc1.compute_count == 2

    # Second instance calls
    assert calc2.add(5, 3) == 8
    assert calc2.compute_count == 1


async def test_no_cache_async_instance_method():
    cache = NoCache()

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

        # First call
        result1 = await calc.multiply(4, 3)
        assert result1 == 12
        assert calc.compute_count == 1

        # Second call should compute again
        result2 = await calc.multiply(4, 3)
        assert result2 == 12
        assert calc.compute_count == 2

    await run_test()


def test_no_cache_with_ignore():
    counter = 0
    cache = NoCache()

    @cache(ignore="ignore_this")
    def get_data(key, ignore_this):
        nonlocal counter
        counter += 1
        return key

    # Should call function every time regardless of ignore parameter
    assert get_data("abc", "ignore_1") == "abc"
    assert counter == 1

    assert get_data("abc", "ignore_2") == "abc"
    assert counter == 2

    assert get_data("def", "ignore_1") == "def"
    assert counter == 3
