def test_shared_cache_between_instances(cache):
    """Test that multiple instances of the same class share the same cache."""
    class DataFetcher:
        """A class that fetches data with caching."""
        def __init__(self):
            self.compute_count = 0

        @cache(per_instance=False)  # Use the global cache fixture with per_instance=False
        def fetch_data(self, key: str) -> str:
            """Fetch data with caching."""
            self.compute_count += 1
            return f"Fetched data for key: {key}"

    # Create two instances of DataFetcher
    fetcher1 = DataFetcher()
    fetcher2 = DataFetcher()

    # First instance first call
    result1 = fetcher1.fetch_data("test_key")
    assert result1 == "Fetched data for key: test_key"
    assert fetcher1.compute_count == 1
    assert fetcher2.compute_count == 0

    # Second instance first call with same input
    result2 = fetcher2.fetch_data("test_key")
    assert result2 == result1  # Should get the same result
    assert fetcher1.compute_count == 1  # Should not compute again
    assert fetcher2.compute_count == 0  # Should use cache

    # First instance second call
    result3 = fetcher1.fetch_data("test_key")
    assert result3 == result1
    assert fetcher1.compute_count == 1  # Should use cache
    assert fetcher2.compute_count == 0

    # Second instance second call
    result4 = fetcher2.fetch_data("test_key")
    assert result4 == result1
    assert fetcher1.compute_count == 1
    assert fetcher2.compute_count == 0


def test_shared_cache_ttl(cache):
    """Test that TTL is respected across instances."""
    class DataFetcher:
        """A class that fetches data with caching."""
        def __init__(self):
            self.compute_count = 0

        @cache(per_instance=False)  # Use the global cache fixture with per_instance=False
        def fetch_data(self, key: str) -> str:
            """Fetch data with caching."""
            self.compute_count += 1
            return f"Fetched data for key: {key}"

    fetcher1 = DataFetcher()
    fetcher2 = DataFetcher()

    # First instance computes and caches
    result1 = fetcher1.fetch_data("test_key")
    assert fetcher1.compute_count == 1
    assert fetcher2.compute_count == 0

    # Second instance should use cache
    result2 = fetcher2.fetch_data("test_key")
    assert result2 == result1
    assert fetcher1.compute_count == 1
    assert fetcher2.compute_count == 0

    # Clear cache
    cache.storage.clear()

    # Second instance should compute new value
    result3 = fetcher2.fetch_data("test_key")
    assert result3 == result1  # Same result but computed again
    assert fetcher1.compute_count == 1
    assert fetcher2.compute_count == 1


def test_shared_cache_with_different_keys(cache):
    """Test that different keys are cached separately."""
    class DataFetcher:
        """A class that fetches data with caching."""
        def __init__(self):
            self.compute_count = 0

        @cache(per_instance=False)  # Use the global cache fixture with per_instance=False
        def fetch_data(self, key: str) -> str:
            """Fetch data with caching."""
            self.compute_count += 1
            return f"Fetched data for key: {key}"

    fetcher1 = DataFetcher()
    fetcher2 = DataFetcher()

    # First instance with first key
    result1 = fetcher1.fetch_data("key1")
    assert fetcher1.compute_count == 1
    assert fetcher2.compute_count == 0

    # Second instance with different key
    result2 = fetcher2.fetch_data("key2")
    assert result2 != result1
    assert fetcher1.compute_count == 1
    assert fetcher2.compute_count == 1

    # Both instances should use cache for their respective keys
    result3 = fetcher1.fetch_data("key1")
    result4 = fetcher2.fetch_data("key2")
    assert result3 == result1
    assert result4 == result2
    assert fetcher1.compute_count == 1
    assert fetcher2.compute_count == 1


def test_per_instance_default_behavior(cache):
    """Test that the default behavior (per_instance=True) creates separate caches."""
    class SeparateCacheFetcher:
        def __init__(self):
            self.compute_count = 0

        @cache  # Default per_instance=True
        def fetch_data(self, key: str) -> str:
            self.compute_count += 1
            return f"Fetched data for key: {key}"

    # Create two instances
    fetcher1 = SeparateCacheFetcher()
    fetcher2 = SeparateCacheFetcher()

    # First instance first call
    result1 = fetcher1.fetch_data("test_key")
    assert fetcher1.compute_count == 1
    assert fetcher2.compute_count == 0

    # Second instance first call with same input
    result2 = fetcher2.fetch_data("test_key")
    assert result2 == result1  # Results should be the same
    assert fetcher1.compute_count == 1  # First instance should not compute again
    assert fetcher2.compute_count == 1  # Second instance should compute once

    # First instance second call
    result3 = fetcher1.fetch_data("test_key")
    assert result3 == result1  # Results should be the same
    assert fetcher1.compute_count == 1  # Should use cache
    assert fetcher2.compute_count == 1  # Should not affect second instance

    # Second instance second call
    result4 = fetcher2.fetch_data("test_key")
    assert result4 == result1  # Results should be the same
    assert fetcher1.compute_count == 1  # Should not affect first instance
    assert fetcher2.compute_count == 1  # Should use cache
