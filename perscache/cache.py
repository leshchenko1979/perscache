import datetime as dt
import functools
import hashlib
import inspect
from typing import Any, Iterable

import cloudpickle

from .serializers import CloudPickleSerializer, Serializer
from .storage import CacheExpired, LocalFileStorage, Storage


def hash_it(*data) -> str:
    """Hashes all the data passed to it as args."""
    result = hashlib.md5()

    for datum in data:
        result.update(cloudpickle.dumps(datum))

    return result.hexdigest()


def is_async(fn):
    return inspect.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn)


class Cache:
    def __init__(self, serializer: Serializer = None, storage: Storage = None):
        self.serializer = serializer or CloudPickleSerializer()
        self.storage = storage or LocalFileStorage()

    @staticmethod
    def get(
        key: str, serializer: Serializer, storage: Storage, deadline: dt.datetime
    ) -> Any:
        data = storage.read(key, deadline)
        return serializer.loads(data)

    @staticmethod
    def set(key: str, value: Any, serializer: Serializer, storage: Storage) -> None:
        data = serializer.dumps(value)
        storage.write(key, data)

    @staticmethod
    def get_key(
        fn: callable,
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

    def get_filename(self, fn: callable, key: str, serializer: Serializer) -> str:
        return f"{fn.__name__}-{key}.{serializer.extension}"

    def cache(
        self,
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

        def decorator(fn):
            ser = serializer or self.serializer
            stor = storage or self.storage

            @functools.wraps(fn)
            def non_async_wrapper(*args, **kwargs):
                key = self.get_key(fn, args, kwargs, ser, ignore)
                key = self.get_filename(fn, key, ser)
                try:
                    deadline = dt.datetime.now(dt.timezone.utc) - ttl if ttl else None
                    return self.get(key, ser, stor, deadline)
                except (FileNotFoundError, CacheExpired):
                    value = fn(*args, **kwargs)
                    self.set(key, value, ser, stor)
                    return value

            @functools.wraps(fn)
            async def async_wrapper(*args, **kwargs):
                key = self.get_key(fn, args, kwargs, ser, ignore)
                key = self.get_filename(fn, key, ser)
                try:
                    deadline = dt.datetime.now(dt.timezone.utc) - ttl if ttl else None
                    return self.get(key, ser, stor, deadline)
                except (FileNotFoundError, CacheExpired):
                    value = await fn(*args, **kwargs)
                    self.set(key, value, ser, stor)
                    return value

            return async_wrapper if is_async(fn) else non_async_wrapper

        return decorator


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

    @staticmethod
    def cache(*decorator_args, **decorator_kwargs):
        """Will call the decorated function every time and
        return its result without any caching.
        """

        def decorator(fn):
            @functools.wraps(fn)
            def non_async_wrapper(*args, **kwargs):
                return fn(*args, **kwargs)

            @functools.wraps(fn)
            async def async_wrapper(*args, **kwargs):
                return await fn(*args, **kwargs)

            return async_wrapper if is_async(fn) else non_async_wrapper

        return decorator
