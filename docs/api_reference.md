
# `perscache` API Reference
- [Base classes](#base-classes)
- [Serializers](#serializers)
- [Storage back-ends](#storage-back-ends)

## Base classes
### class `perscache.Cache()`
#### Parameters
- `serializer (perscache.serializers.Serializer)`: a serializer class to use for converting stored data. Defaults to `perscache.serlializers.PickleSerializer`.

- `storage (perscache.storage.Storage)`: a storage back-end used to save and load data. Defaults to `perscache.storage.LocalFileStorage`.

#### decorator `perscache.Cache().__call__()`
Tries to find a cached result of the decorated function in persistent storage. Returns the saved result if it was found, or calls the decorated function and caches its result.

Usage:
```python
from perscache import Cache

cache = Cache()

@cache
def get_data():
    ...
```

The cache will be invalidated if the function code, its argument values or the cache serializer have been changed.

This method emits some log messages with a logger named `perscache`. Add a handler to the logger to see the messages:
```python
import logging

logging.getLogger('perscache').addHandler(logging.StreamHandler())
```
##### Arguments
- `ignore (str | Iterable[str])`: arguments of the decorated function that will not be used in making the cache key. In other words, changes in these arguments will not invalidate the cache. Defaults to `None`.

- `serializer (perscache.serializers.Serializer)`: Overrides the default `Cache()` serializer. Defaults to `None`.

- `storage (perscache.storage.Storage)`: Overrides the default `Cache()` storage. Defaults to `None`.

- `ttl (datetime.timedelta)`: The time-to-live of the cache for the decorated function. If `None`, the cache never exprires. Defaults to `None`.

### class `perscache.NoCache()`
This class has no parameters. It is useful to [alternate cache behaviour depending on the environment](../README.md#alternating-cache-settings-depending-on-the-environment).
#### decorator `perscache.NoCache().__call__()`
The underlying function will be called every time the decorated function has been called and no caching will take place.

This decorator will ignore any parameters it has been given.

## Serializers
Serializers are imported from the `perscache.serializers` module.

To see which serializers are compatible with which data types, see the [compatibility.py](/perscache/compatibility.py) file.


### class `perscache.serializers.Serializer`
The abstract base serializer class.

See also [how to make your own serializer](/README.md#make-your-own-serialization-and-storage-backends).

### function `perscache.serializers.make_serializer()`
This function is used to create a serializer class.

#### Arguments
- `class_name (str)`: the name of the serializer class.
- `ext (str)`: the extension of the serialized file.
- `dumps_fn (Callable)`: the function used to serialize an object into bytes. Accepts a single argument, the object to serialize, and returns a bytes object.
- `loads_fn (Callable)`: the function used to deserialize bytes into an object. Accepts a single argument, the bytes to deserialize, and returns an object.

#### Returns
A serializer class derived from `perscache.serializers.Serializer` that can be used with `perscache.Cache`.

#### Example
```python
from perscache.serializers import make_serializer
from perscache import Cache

PyrogramSerializer = make_serializer(
    class_name = 'PyrogramSerializer',
    ext = 'pyrogram',
    dumps_fn = lambda x: str(x).encode('utf-8'),
    loads_fn = lambda x: eval(x.decode('utf-8')),
)

cache = Cache()

@cache(serializer=PyrogramSerializer())
def get_data():
    ...
```

### class `perscache.serializers.CloudPickleSerializer`
Uses the `cloudpickle` module. It's the most capable serializer of all, able to process most of the data types.

It's the default serializer for the `Cache` class.
### class `perscache.serializers.JSONSerializer`
Uses the `json` module.
### class `perscache.serializers.YAMLSerializer`
Uses the `yaml` module.
### class `perscache.serializers.PickleSerializer`
Uses the `pickle` module.
### class `perscache.serializers.CSVSerializer`
Uses the `pandas` module. Processes `pandas.DataFrame` objects.
### class `perscache.serializers.ParquetSerializer`
Uses the `pyarrow` module. Processes `pandas.DataFrame` objects.
#### Parameters
- `compression (str)`: compression used by `pyarrow` to save the data. Defaults to `"brotli"`.

## Storage back-ends
Storage back-ends are imported from the `perscache.storage` module.

See also [how to make your own storage back-end](/README.md#make-your-own-serialization-and-storage-backends).

### class `perscache.storage.LocalFileStorage`
Keeps cache entries in separate files in a file system directory.

This is the default storage class used by `Cache`.
#### Parameters
- `location (str)`: a directory to store the cache files. Defaults to `".cache"`.

- `max_size (int)`: the maximum size for the cache. If set, then, before a new cache entry is written, the future size of the directory is calculated and the least recently used cache entries are removed. If `None`, the cache grows indefinitely. Defaults to `None`.

### class `perscache.storage.GoogleCloudStorage`
Keeps cache entries in separate files in a Google Cloud Storage Bucket.

Relies on the [`gcsfs`](https://pypi.org/project/gcsfs/) module, which is not a part of the project dependencies and needs to to be installed by the user if he is to use this class.

#### Parameters
- `location (str)`: a directory to store the cache files. Defaults to `".cache"`.

- `max_size (int)`: the maximum size for the cache. If set, then, before a new cache entry is written, the future size of the directory is calculated and the least recently used cache entries are removed. If `None`, the cache size grows indefinitely. Defaults to `None`.

- `storage_options (dict)`: a dictionary of parameters to pass to the constructor of the `GSCFilesystem` class of the [`gcsfs`](https://pypi.org/project/gcsfs/) module (see the module documentation for more information). Defaults to `None`.

```python
# supposing gcsfs is installed

from perscache import Cache
from perscache.storage import GoogleCloudStorage

cache = Cache(
    storage=GoogleCloudStorage(
        location="my-bucket/cache",
        storage_options={"token": "my-token.json"}
    )
)

@cache
def get_data():
    ...
```
