import functools
import inspect
from typing import Any

from .serializers import Serializer, PickleSerializer
from .storage import Storage, LocalFileStorage

def body_arg_hash(fn: callable, args: tuple, kwargs: dict) -> str:
    """Returns a string that uniquely identifies the body of the function
    and its given arguments through hashing."""
    import hashlib

    result = hashlib.md5()

    result.update(inspect.getsource(fn).encode("utf-8"))
    result.update(str(args).encode("utf-8"))
    result.update(str(kwargs).encode("utf-8"))

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
        fn: callable,
        args: tuple,
        kwargs: dict,
        cache_fn: callable,
        ignore=None,
    ) -> str:
        # Remove ignored arguments from the arguments tuple and kwargs dict
        if ignore is not None:
            kwargs = {k: v for k, v in kwargs.items() if k not in ignore}

        return cache_fn(fn, args, kwargs)

    def get_filename(self, fn: callable, key: str, serializer: Serializer) -> str:
        return f"{fn.__name__}-{key}.{serializer.extension}"

    def cache(
        self,
        cache_fn: callable = body_arg_hash,
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
                key = self.get_key(fn, args, kwargs, cache_fn, ignore)
                key = self.get_filename(fn, key, ser)
                try:
                    return self.get(key, ser, stor)
                except FileNotFoundError:
                    value = fn(*args, **kwargs)
                    self.set(key, value, ser, stor)
                    return value

            @functools.wraps(fn)
            async def async_wrapper(*args, **kwargs):
                key = self.get_key(fn, args, kwargs, cache_fn, ignore)
                key = self.get_filename(fn, key, ser)
                try:
                    return self.get(key, ser, stor)
                except FileNotFoundError:
                    value = await fn(*args, **kwargs)
                    self.set(key, value, ser, stor)
                    return value

            return async_wrapper if self.is_async(fn) else non_async_wrapper

        return decorator
