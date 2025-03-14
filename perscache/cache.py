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
        per_instance: bool = True,
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
            per_instance: Whether to create a separate cache for each instance of a class.
                    Defaults to True.
        """

        if isinstance(ignore, str):
            ignore = [ignore]

        wrapper = _CachedFunction(
            self, ignore, serializer or self.serializer, storage or self.storage, ttl, per_instance
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
        per_instance: bool = True,
    ) -> str:
        debug("Generating hash for function: %s", fn.__name__)

        # Get source code from the function
        source = inspect.getsource(fn)
        debug(
            "Function source hash input: %s",
            f"{source[:100]}..." if len(source) > 100 else source,
        )

        # Build argument dictionary
        arg_dict = {}
        params = list(inspect.signature(fn).parameters.values())
        ignore_set = set(ignore) if ignore is not None else set()
        debug("Ignoring parameters: %s", ignore_set)

        # Process arguments, skipping ignored ones and self when per_instance=False
        start_idx = 1 if instance_id is not None else 0
        for i, param in enumerate(params[start_idx:], start=start_idx):
            if param.name not in ignore_set and (per_instance or param.name != 'self'):
                if i < len(args):
                    arg_dict[param.name] = args[i]
                elif param.name in kwargs:
                    arg_dict[param.name] = kwargs[param.name]

        debug("Final argument dictionary: %s", arg_dict)

        # Build hash components
        hash_components = [source, type(serializer).__name__, arg_dict]
        if instance_id is not None and per_instance:
            hash_components.insert(0, str(instance_id))

        hash_value = hash_it(*hash_components)
        debug("Generated hash: %s", hash_value)
        return hash_value

    def _get_filename(self, fn: Callable, key: str, serializer: Serializer) -> str:
        if inspect.ismethod(fn):
            class_name = fn.__self__.__class__.__name__
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
    """An internal class used as a wrapper."""

    @beartype
    def __init__(
        self,
        cache: Cache,
        ignore: Optional[Iterable[str]],
        serializer: Serializer,
        storage: Storage,
        ttl: Optional[dt.timedelta],
        per_instance: bool = True,
    ):
        self.cache = cache
        self.ignore = ignore
        self.serializer = serializer
        self.storage = storage
        self.ttl = ttl
        self.per_instance = per_instance

    @require(
        lambda self, fn: self.ignore is None
        or all(x in inspect.signature(fn).parameters for x in self.ignore),
        "Ignored parameters not found in the function signature.",
    )
    def __call__(self, fn: Callable) -> Callable:
        """Return the correct wrapper."""

        def is_instance_method(args):
            return (args and hasattr(type(args[0]), fn.__name__)
                   and not isinstance(args[0], (str, bytes, int, float, bool)))

        def create_wrapper(is_async_wrapper):
            @functools.wraps(fn)
            def wrapped(*args, **kwargs):
                if is_instance_method(args):
                    bound_method = types.MethodType(fn, args[0])
                    instance_id = id(args[0]) if self.per_instance else None
                    return (is_async_wrapper(bound_method, instance_id, *args, **kwargs)
                           if is_async_wrapper else
                           self._non_async_wrapper(bound_method, instance_id, *args, **kwargs))
                return (is_async_wrapper(fn, None, *args, **kwargs)
                       if is_async_wrapper else
                       self._non_async_wrapper(fn, None, *args, **kwargs))
            return wrapped

        if is_async(fn):
            return create_wrapper(self._async_wrapper)
        return create_wrapper(self._non_async_wrapper)

    def _non_async_wrapper(self, fn: Callable, instance_id: Optional[int], *args, **kwargs):
        debug("Entering cache wrapper for function: %s", fn.__name__)
        debug("Args: %s, Kwargs: %s", args, kwargs)

        # Handle instance methods
        if inspect.ismethod(fn):
            instance = fn.__self__
            debug("Detected instance method - class: %s, instance_id: %s",
                  instance.__class__.__name__, instance_id)
            # Get the underlying function and skip self parameter
            func = fn.__func__
            key = self.cache._get_hash(func, args, kwargs, self.serializer, self.ignore, instance_id, self.per_instance)
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
            # For bound methods, skip the first argument (self)
            if inspect.ismethod(fn):
                value = fn(*args[1:], **kwargs)
            else:
                value = fn(*args, **kwargs)
            debug("Caching new value for key: %s", key)
            self.cache._set(key, value, self.serializer, self.storage)
            return value

    async def _async_wrapper(self, fn: Callable, instance_id: Optional[int], *args, **kwargs):
        debug("Entering async cache wrapper for function: %s", fn.__name__)
        debug("Args: %s, Kwargs: %s", args, kwargs)

        # Handle instance methods
        if inspect.ismethod(fn):
            instance = fn.__self__
            debug("Detected instance method - class: %s, instance_id: %s",
                  instance.__class__.__name__, instance_id)
            # Get the underlying function and skip self parameter
            func = fn.__func__
            key = self.cache._get_hash(func, args, kwargs, self.serializer, self.ignore, instance_id, self.per_instance)
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
            # For bound methods, skip the first argument (self)
            if inspect.ismethod(fn):
                value = await fn(*args[1:], **kwargs)
            else:
                value = await fn(*args, **kwargs)
            debug("Caching new value for key: %s", key)
            self.cache._set(key, value, self.serializer, self.storage)
            return value

    @property
    def deadline(self) -> dt.datetime:
        """Return the deadline for the cache."""
        return dt.datetime.now(dt.timezone.utc) - self.ttl if self.ttl else None
