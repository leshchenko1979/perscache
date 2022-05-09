"""An easy to use decorator for persistent memoization.

Like `functools.lrucache`, but results can be saved in any format to any storage.
"""

import datetime as dt
import functools
import hashlib
import inspect
from typing import Any, Callable, Iterable

import cloudpickle

from .serializers import CloudPickleSerializer, Serializer
from .storage import CacheExpired, LocalFileStorage, Storage


def hash_it(*data) -> str:
    """Pickles and hashes all the data passed to it as args."""
    result = hashlib.md5()

    for datum in data:
        result.update(cloudpickle.dumps(datum))

    return result.hexdigest()


def is_async(fn):
    """Checks if the function is async."""
    return inspect.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn)


class Cache:
    """A cache that can be used to memoize functions."""

    def __init__(self, serializer: Serializer = None, storage: Storage = None):
        """Initialize the cache.

        Args:
            serializer: The serializer to use. If not specified, CloudPickleSerializer is used.
            storage: The storage to use. If not specified, LocalFileStorage is used.
        """

        self.serializer = serializer or CloudPickleSerializer()
        self.storage = storage or LocalFileStorage()

    def __repr__(self) -> str:
        return f"<Cache(serializer={self.serializer}, storage={self.storage})>"

    def __call__(
        self,
        fn: callable = None,
        *,
        ignore: Iterable[str] = None,
        serializer: Serializer = None,
        storage: Storage = None,
        ttl: dt.timedelta = None,
    ):
        """Cache the value of the wrapped function.

        Tries to find a cached result of the decorated function in persistent storage.
        Returns the saved result if it was found, or calls the decorated function
        and caches its result.

        The cache will be invalidated if the function code, its argument values or
        the cache serializer have been changed.

        Args:
            ignore: A list of argument names to ignore when hashing the function.
            serializer: The serializer to use. If not specified, the default serializer is used.
                    Defaults to None.
            storage: The storage to use. If not specified, the default storage is used.
                    Defaults to None.
            ttl: The expiration time of the cache. If None, the cache will never expire.
                    Defaults to None.
        """

        wrapper = CachedFunction(
            self, ignore, serializer or self.serializer, storage or self.storage, ttl
        )

        # The decorator should work both with and without parentheses
        return wrapper if fn is None else wrapper(fn)

    cache = __call__  # Alias for backwards compatibility.

    @staticmethod
    def _get(
        key: str, serializer: Serializer, storage: Storage, deadline: dt.datetime
    ) -> Any:
        data = storage.read(key, deadline)
        return serializer.loads(data)

    @staticmethod
    def _set(key: str, value: Any, serializer: Serializer, storage: Storage) -> None:
        data = serializer.dumps(value)
        storage.write(key, data)

    @staticmethod
    def _get_key(
        fn: Callable,
        args: tuple,
        kwargs: dict,
        serializer: Serializer,
        ignore: Iterable[str],
    ) -> str:
        """Get a cache key."""

        # Remove ignored arguments from the arguments tuple and kwargs dict
        if ignore is not None:
            kwargs = {k: v for k, v in kwargs.items() if k not in ignore}

        return hash_it(inspect.getsource(fn), type(serializer), args, kwargs)

    def _get_filename(self, fn: callable, key: str, serializer: Serializer) -> str:
        return f"{fn.__name__}-{key}.{serializer.extension}"


class NoCache:
    """A class used to turn off caching.

    Example:
    ```
    cache = NoCache() if os.environ["DEBUG"] else Cache()

    @cache.cache
    def function():
        ...
    ```
    """

    def __repr__(self) -> str:
        return "<NoCache>"

    @staticmethod
    def __call__(*decorator_args, **decorator_kwargs):
        """Will call the decorated function every time and
        return its result without any caching.
        """

        def _decorator(fn):
            @functools.wraps(fn)
            def _non_async_wrapper(*args, **kwargs):
                return fn(*args, **kwargs)

            @functools.wraps(fn)
            async def _async_wrapper(*args, **kwargs):
                return await fn(*args, **kwargs)

            return _async_wrapper if is_async(fn) else _non_async_wrapper

        return _decorator

    cache = __call__  # Alias for backwards compatibility.


class CachedFunction:
    """A class used as a wrapper."""

    def __init__(
        self,
        cache: Cache,
        ignore: Iterable[str],
        serializer: Serializer,
        storage: Storage,
        ttl: dt.timedelta,
    ):
        self.cache = cache
        self.ignore = ignore
        self.serializer = serializer
        self.storage = storage
        self.ttl = ttl

    def __repr__(self) -> str:
        return (
            f"<CachedFunction(cache={self.cache}, ignore={self.ignore}, "
            "serializer={self.serializer}, storage={self.storage}, ttl={self.ttl})>"
        )

    def __call__(self, fn):
        """Return the correct wrapper."""

        @functools.wraps(fn)
        def _non_async_wrapper(*args, **kwargs):
            key = self.cache._get_key(fn, args, kwargs, self.serializer, self.ignore)
            key = self.cache._get_filename(fn, key, self.serializer)
            try:
                deadline = (
                    dt.datetime.now(dt.timezone.utc) - self.ttl if self.ttl else None
                )
                return self.cache._get(key, self.serializer, self.storage, deadline)
            except (FileNotFoundError, CacheExpired):
                value = fn(*args, **kwargs)
                self.cache._set(key, value, self.serializer, self.storage)
                return value

        @functools.wraps(fn)
        async def _async_wrapper(*args, **kwargs):
            key = self.cache._get_key(fn, args, kwargs, self.serializer, self.ignore)
            key = self.cache._get_filename(fn, key, self.serializer)
            try:
                deadline = (
                    dt.datetime.now(dt.timezone.utc) - self.ttl if self.ttl else None
                )
                return self.cache._get(key, self.serializer, self.storage, deadline)
            except (FileNotFoundError, CacheExpired):
                value = await fn(*args, **kwargs)
                self.cache._set(key, value, self.serializer, self.storage)
                return value

        return _async_wrapper if is_async(fn) else _non_async_wrapper
