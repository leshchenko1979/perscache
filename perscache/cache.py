"""An easy to use decorator for persistent memoization.

Like `functools.lrucache`, but results can be saved in any format to any storage.
"""

import datetime as dt
import functools
import hashlib
import inspect
import types

import cloudpickle
from beartype import beartype
from beartype.typing import Any, Callable, Iterable, Optional
from icontract import require

from .serializers import CloudPickleSerializer, Serializer
from .storage import CacheExpired, LocalFileStorage, Storage
from ._logger import debug, trace


def hash_it(*data) -> str:
    """Pickles and hashes all the data passed to it as args."""
    result = hashlib.md5()  # nosec B303

    for datum in data:
        result.update(cloudpickle.dumps(datum))

    return result.hexdigest()


def is_async(fn):
    """Checks if the function is async."""
    return inspect.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn)


class Cache:
    """A cache that can be used to memoize functions."""

    @beartype
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

    @beartype
    @require(
        lambda ttl: ttl is None or ttl > dt.timedelta(seconds=0),
        "ttl must be positive.",
    )
    def __call__(
        self,
        fn: Optional[Callable] = None,
        *,
        ignore: Optional[Iterable[str]] = None,
        serializer: Optional[Serializer] = None,
        storage: Optional[Storage] = None,
        ttl: Optional[dt.timedelta] = None,
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

        if isinstance(ignore, str):
            ignore = [ignore]

        wrapper = _CachedFunction(
            self, ignore, serializer or self.serializer, storage or self.storage, ttl
        )

        # The decorator should work both with and without parentheses
        return wrapper if fn is None else wrapper(fn)

    cache = __call__  # Alias for backwards compatibility.

    @staticmethod
    @trace
    def _get(
        key: str, serializer: Serializer, storage: Storage, deadline: dt.datetime
    ) -> Any:
        data = storage.read(key, deadline)
        return serializer.loads(data)

    @staticmethod
    @trace
    def _set(key: str, value: Any, serializer: Serializer, storage: Storage) -> None:
        data = serializer.dumps(value)
        storage.write(key, data)

    @staticmethod
    def _get_hash(
        fn: Callable,
        args: tuple,
        kwargs: dict,
        serializer: Serializer,
        ignore: Iterable[str],
        instance_id: Optional[int] = None,
    ) -> str:
        debug("Generating hash for function: %s", fn.__name__)

        # Get source code from the function
        source = inspect.getsource(fn)
        debug("Function source hash input: %s", source[:100] + "..." if len(source) > 100 else source)

        # Build argument dictionary
        arg_dict = {}
        params = list(inspect.signature(fn).parameters.values())

        # Get list of parameters to ignore
        ignore_set = set(ignore) if ignore is not None else set()
        debug("Ignoring parameters: %s", ignore_set)

        # Process arguments, skipping ignored ones
        param_index = 0
        for param in params:
            if param.name not in ignore_set:
                if param_index < len(args):
                    arg_dict[param.name] = args[param_index]
                elif param.name in kwargs:
                    arg_dict[param.name] = kwargs[param.name]
            param_index += 1

        debug("Final argument dictionary: %s", arg_dict)

        # Build hash components
        hash_components = [source, type(serializer).__name__]
        if instance_id is not None:
            # For instance methods, add instance ID before arguments
            hash_components.extend([instance_id, arg_dict])
        else:
            hash_components.append(arg_dict)

        hash_value = hash_it(*hash_components)
        debug("Generated hash: %s", hash_value)
        return hash_value

    def _get_filename(self, fn: Callable, key: str, serializer: Serializer) -> str:
        if inspect.ismethod(fn):
            class_name = fn.__self__.__class__.__name__
            instance_id = id(fn.__self__)
            filename = f"{class_name}.{fn.__name__}-{key}.{serializer.extension}"
            debug("Generated instance method cache filename: %s", filename)
            return filename
        filename = f"{fn.__name__}-{key}.{serializer.extension}"
        debug("Generated function cache filename: %s", filename)
        return filename


class NoCache:
    """A class used to turn off caching.

    Example:
    ```
    cache = NoCache() if os.environ["DEBUG"] else Cache()

    @cache
    def function():
        ...
    ```
    """

    def __repr__(self) -> str:
        return "<NoCache>"

    def __call__(self, *decorator_args, **decorator_kwargs):
        """Will call the decorated function every time and
        return its result without any caching.
        """
        if decorator_args and callable(decorator_args[0]):
            return self._decorator(decorator_args[0])
        return self._decorator

    def _decorator(self, fn):
        @functools.wraps(fn)
        def _non_async_wrapper(*args, **kwargs):
            return fn(*args, **kwargs)

        @functools.wraps(fn)
        async def _async_wrapper(*args, **kwargs):
            return await fn(*args, **kwargs)

        return _async_wrapper if is_async(fn) else _non_async_wrapper

    cache = __call__  # Alias for backwards compatibility.


class _CachedFunction:
    """An interal class used as a wrapper."""

    @beartype
    def __init__(
        self,
        cache: Cache,
        ignore: Optional[Iterable[str]],
        serializer: Serializer,
        storage: Storage,
        ttl: Optional[dt.timedelta],
    ):
        self.cache = cache
        self.ignore = ignore
        self.serializer = serializer
        self.storage = storage
        self.ttl = ttl

    @require(
        lambda self, fn: self.ignore is None
        or all(x in inspect.signature(fn).parameters for x in self.ignore),
        "Ignored parameters not found in the function signature.",
    )
    def __call__(self, fn: Callable) -> Callable:
        """Return the correct wrapper."""

        if is_async(fn):
            @functools.wraps(fn)
            async def wrapped(*args, **kwargs):
                # Check if this is an instance method call by looking at the first argument
                if args and hasattr(type(args[0]), fn.__name__) and not isinstance(args[0], (str, bytes, int, float, bool)):
                    # Create a bound method
                    bound_method = types.MethodType(fn, args[0])
                    return await self._async_wrapper(bound_method, *args, **kwargs)
                return await self._async_wrapper(fn, *args, **kwargs)
        else:
            @functools.wraps(fn)
            def wrapped(*args, **kwargs):
                # Check if this is an instance method call by looking at the first argument
                if args and hasattr(type(args[0]), fn.__name__) and not isinstance(args[0], (str, bytes, int, float, bool)):
                    # Create a bound method
                    bound_method = types.MethodType(fn, args[0])
                    return self._non_async_wrapper(bound_method, *args, **kwargs)
                return self._non_async_wrapper(fn, *args, **kwargs)

        return wrapped

    def _non_async_wrapper(self, fn: Callable, *args, **kwargs):
        debug("Entering cache wrapper for function: %s", fn.__name__)
        debug("Args: %s, Kwargs: %s", args, kwargs)

        # Handle instance methods
        if inspect.ismethod(fn):
            instance = fn.__self__
            instance_id = id(instance)
            debug("Detected instance method - class: %s, instance_id: %s",
                  instance.__class__.__name__, instance_id)
            # Get the underlying function and skip self parameter
            func = fn.__func__
            args = args[1:]  # Remove self from args
            key = self.cache._get_hash(func, args, kwargs, self.serializer, self.ignore, instance_id)
        else:
            debug("Detected standalone function")
            key = self.cache._get_hash(fn, args, kwargs, self.serializer, self.ignore)

        key = self.cache._get_filename(fn, key, self.serializer)
        try:
            debug("Attempting to retrieve cached result for key: %s", key)
            result = self.cache._get(key, self.serializer, self.storage, self.deadline)
            debug("Cache hit - retrieved value for key: %s", key)
            return result
        except (FileNotFoundError, CacheExpired) as exception:
            debug("Cache miss for %s: %s", fn.__name__, exception)
            value = fn(*args, **kwargs)
            debug("Caching new value for key: %s", key)
            self.cache._set(key, value, self.serializer, self.storage)
            return value

    async def _async_wrapper(self, fn: Callable, *args, **kwargs):
        debug("Entering async cache wrapper for function: %s", fn.__name__)
        debug("Args: %s, Kwargs: %s", args, kwargs)

        # Handle instance methods
        if inspect.ismethod(fn):
            instance = fn.__self__
            instance_id = id(instance)
            debug("Detected instance method - class: %s, instance_id: %s",
                  instance.__class__.__name__, instance_id)
            # Get the underlying function and skip self parameter
            func = fn.__func__
            args = args[1:]  # Remove self from args
            key = self.cache._get_hash(func, args, kwargs, self.serializer, self.ignore, instance_id)
        else:
            debug("Detected standalone function")
            key = self.cache._get_hash(fn, args, kwargs, self.serializer, self.ignore)

        key = self.cache._get_filename(fn, key, self.serializer)
        try:
            debug("Attempting to retrieve cached result for key: %s", key)
            result = self.cache._get(key, self.serializer, self.storage, self.deadline)
            debug("Cache hit - retrieved value for key: %s", key)
            return result
        except (FileNotFoundError, CacheExpired) as exception:
            debug("Cache miss for %s: %s", fn.__name__, exception)
            value = await fn(*args, **kwargs)
            debug("Caching new value for key: %s", key)
            self.cache._set(key, value, self.serializer, self.storage)
            return value

    @property
    def deadline(self) -> dt.datetime:
        """Return the deadline for the cache."""
        return dt.datetime.now(dt.timezone.utc) - self.ttl if self.ttl else None
