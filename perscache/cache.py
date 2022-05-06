import functools
import hashlib
import inspect
from typing import Any

from .serializers import PickleSerializer, Serializer
from .storage import LocalFileStorage, Storage


def hash_it(*data) -> str:
    """Hashes all the data passed to it as args."""
    result = hashlib.md5()

    for datum in data:
        result.update(str(datum).encode("utf-8"))

    return result.hexdigest()


class Cache:
    def __init__(self, serializer: Serializer = None, storage: Storage = None):
        self.serializer = serializer or PickleSerializer()
        self.storage = storage or LocalFileStorage()

    @staticmethod
    def get(key: str, serializer: Serializer, storage: Storage) -> Any:
        data = storage.read(key)
        return serializer.loads(data)

    @staticmethod
    def set(key: str, value: Any, serializer: Serializer, storage: Storage) -> None:
        data = serializer.dumps(value)
        storage.write(key, data)

    @staticmethod
    def is_async(fn):
        return inspect.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn)

    @staticmethod
    def get_key(
        fn: callable, args: tuple, kwargs: dict, serializer: Serializer, ignore=None
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
        ignore=None,
        serializer: Serializer = None,
        storage: Storage = None,
    ):
        """A method that returns a decorator that would wrap the passed in function
        and cache its return value based on the first argument.
        """

        def decorator(fn):
            ser = serializer or self.serializer
            stor = storage or self.storage

            @functools.wraps(fn)
            def non_async_wrapper(*args, **kwargs):
                key = self.get_key(fn, args, kwargs, ser, ignore)
                key = self.get_filename(fn, key, ser)
                try:
                    return self.get(key, ser, stor)
                except FileNotFoundError:
                    value = fn(*args, **kwargs)
                    self.set(key, value, ser, stor)
                    return value

            @functools.wraps(fn)
            async def async_wrapper(*args, **kwargs):
                key = self.get_key(fn, args, kwargs, ser, ignore)
                key = self.get_filename(fn, key, ser)
                try:
                    return self.get(key, ser, stor)
                except FileNotFoundError:
                    value = await fn(*args, **kwargs)
                    self.set(key, value, ser, stor)
                    return value

            return async_wrapper if self.is_async(fn) else non_async_wrapper

        return decorator
