from perscache import NoCache

def test_no_cache_with_parentheses():

    cache = NoCache()
    @cache()
    def dummy_func():
        return 'NoCache with parentheses'

    assert dummy_func() == 'NoCache with parentheses'

def test_no_cache_without_parentheses():
    cache = NoCache()

    @cache
    def dummy_func():
        return 'NoCache without parentheses'

    assert dummy_func() == 'NoCache without parentheses'
