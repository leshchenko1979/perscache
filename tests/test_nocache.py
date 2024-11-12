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
    cache = NoCache()

    @cache
    def dummy_func():
        return 'NoCache without parentheses'

    assert dummy_func() == 'NoCache without parentheses'


async def test_no_cache_with_parentheses_async():
    cache = NoCache()

    @cache()
    async def dummy_func():
        return 'NoCache with parentheses async'

    assert await dummy_func() == 'NoCache with parentheses async'


async def test_no_cache_without_parentheses_async():
    cache = NoCache()

    @cache
    async def dummy_func():
        return 'NoCache without parentheses async'

    assert await dummy_func() == 'NoCache without parentheses async'
