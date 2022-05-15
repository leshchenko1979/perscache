# perscache

![](https://img.shields.io/pypi/dm/perscache.svg)
![](https://github.com/leshchenko1979/perscache/workflows/build/badge.svg)
[![codecov](https://codecov.io/gh/leshchenko1979/perscache/branch/master/graph/badge.svg?token=IVIIFN8NDU)](https://codecov.io/gh/leshchenko1979/perscache)
[![CodeFactor](https://www.codefactor.io/repository/github/leshchenko1979/perscache/badge)](https://www.codefactor.io/repository/github/leshchenko1979/perscache)

An easy to use decorator for persistent memoization: like `functools.lrucache`, but results persist between runs and can be stored in any format to any storage.
```python
from perscache import Cache

cache = Cache()

@cache
def get_data():
    ...
```
## Contents
- [Use cases](#use-cases)
- [Features](#features)
- [Getting started](#getting-started)
- [Make your own serialization and storage back-ends](#make-your-own-serialization-and-storage-backends)
- [API Reference](docs/api_reference.md)


## Use cases
- Cache the results of a function that uses a lot of resources: runs for a long time, consumes a lot of traffic, uses up paid API calls etc.
- Speed up retreival of data that doesn't change often.
- Inspect the results of a decorated function while debugging.
- Build a simple data store.

## Features
### Caching
- Easy to swap out the cache configuration when switching environments.
- Async functions supported.
- Time-to-live (TTL) support - automatically invalidate cache entries after a certain time.
- Automatic cache invalidation when the decorated function arguments or code have been changed.
- You can ignore changes in certain arguments of the decorated function.

### Serialization and storage
- Various serialization formats: JSON, YAML, pickle, Parquet, CSV etc.
- Various storage backends: local disk, GCS (Google Cloud Storage) and others to be implemented soon ([S3](https://github.com/leshchenko1979/perscache/issues/13), [Azure Blob Storage](https://github.com/leshchenko1979/perscache/issues/14)).
- Serialization and storage are separated into two different classes, so that you can mix various serialization formats and storage back-ends as you like - JSON to local storage, Pickle to AWS, Parquet to Google Cloud Storage etc.
- You can set default serialization format and storage backend and then change them on a per-function basis.
- You can easily add new serialization formats and storage back-ends.
- Local storage is file-based, so you can use human-readable serialization (JSON, YAML, CSV) and inspect cached results.
- Automatic cleanup: least recently used results can be removed from storage when the total storage size exceeds a given threshold.

## Getting started
### Installation
```bash
pip install perscache
```
There are also some optional dependencies you need to install to use some of the features:
- `yaml` - for YAML serialization
- `pyarrow` - for Parquet serialization
- `pandas` - for CSV serialization
- `gcsfs` - for GCS storage
### Basic usage
```python
from perscache import Cache

cache = Cache()

counter = 0

@cache
def get_data():
    print("Fetching data...")

    global counter
    counter += 1

    return "abc"

print(get_data())  # the function is called
# Fetching data...
# abc

print(get_data())  # the cache is used
# abc

print(counter)  # the function was called only once
# 1
```

### Changing parameters or the code of the function invalidates the cache
```python
@cache
def get_data(key):
    print("The function has been called...")
    return key

print(get_data("abc"))  # the function has been called
# The function has been called...
# abc

print(get_data("fgh"))  # the function has been called again
# The function has been called...
# fgh

print(get_data("abc"))  # using the cache
# abc

@cache
def get_data(key):
    print("This function has been changed...")
    return key

print(get_data("abc"))  # the function has been called again
# This function has been changed...
# abc

```
>NOTE: `perscache` hashes the function arguments, its code and the name of the class of the serializer, so that the cache is invalidated when any of these change. You can use the `ignore_args` parameter to [ignore changes in certain arguments](#ignoring-certain-arguments) of the decorated function.
>
>However, if you change the code of the serializer, the cache is not invalidated. (This is because we cannot hash the code of the serializer when in was made with the factory function `make_serializer`. See [Make your own serialization and storage back-ends](#make-your-own-serialization-and-storage-backends) for more details.)
### Setting the expiry time of the cache
```python
import datetime as dt

@cache(ttl=dt.timedelta(days=1))
def get_data():
    """This function will be cached for 1 day
    and called again after this period expires."""
    ...
```
### Ignoring certain arguments
By specifying the arguments that should be ignored, you can still use the cache even in the values of these arguments have changed.
```python
@cache(ignore="ignore_this")
def get_data(key, ignore_this):
    print("The function has been called...")
    return key

print(get_data("abc", "ignore_1"))  # the function has been called
# The function has been called...
# abc

# using the cache although the the second argument is different
print(get_data("abc", "ignore_2"))
# abc
```

### Changing the default serialization format and storage backend
```python
# set up serialization format and storage backend
cache = Cache(
    serializer=JSONSerializer(),
    storage=GoogleCloudStorage("/bucket/folder")
)

...

# change the default serialization format
@cache(serialization=PickleSerializer())
def get_data(key):
    ...
```

### Alternating cache settings depending on the environment
```python
import os

from perscache import Cache, NoCache
from perscache.storage import LocalFileStorage

if os.environ.get["DEBUG"]:
    cache = NoCache()  # turn off caching in debug mode
else:
    cache = (
        GoogleCloudStorage("/bucket/folder")
        if os.environ.get["GOOGLE_PROJECT_NAME"]  # if running in the cloud
        else LocalFileStorage()
    )

@cache
def function():
    ...
```
### Inspecting cached results
Use human-readable serialization (`JSONSerializer`, `YAMLSerializer`, `CSVSerializer`) and a file storage (`LocalFileStorage`, `GoogleCloudStorage`) to inspect cached results.

### Automatic cleanup
When using `LocalFileStorage(max_size=...)` or `GoogleCloudStorage(max_size=...)` , the least recently used cache entries are automatically removed to keep the total cache size with the `max_size` limit.

## Make your own serialization and storage backends
### Serializers
Although you can use the standard `CloudPickleSerializer()` for almost any type of data, sometimes you want to inspect the results of a decorated function by lookin into the cache files. This requires the data to be serialized in a human-readable format. But the included human-readable serializers (`JSONSerializer()`, `YAMLSerializer()`, `CSVSerializer()`) sometimes cannot process complex objects.

>To see which serializers are compatible with which data types, see the [compatibility.py](/perscache/compatibility.py) file.

That's when making your own serializer comes in handy.

To do this, you should:
1. Derive your own serialization classe from the abstract `Serializer` class and override the abstract methods. You should also provide the `extension` class variable that specifies the file extension.
2. Use your class with the `Cache` class.

```python
from perscache.serializers import Serializer

class MySerializer(Serializer):

    extension = "data"

    def dumps(self, data: Any) -> bytes:
        ...

    def loads(self, data: bytes) -> Any:
        ...

cache = Cache(serializer=MySerializer())
```
#### Serializer factory
You can also use the `perscache.serializers.make_serializer()` function to create a serializer for a given data type.
```python
import pyrogram
from perscache.serializers import make_serializer

PyrogramSerializer = make_serializer(
    "PyrogramSerializer",
    "pyro",
    dumps_fn = lambda data: str(data).encode("utf-8"),
    loads_fn = lambda data: eval(data.decode("utf-8")),
)

cache = Cache(serializer=PyrogramSerializer())

@cache
async def some_pyrogram_func() -> pyrogram.Message:
    ...
```
### Storage back-ends
Making a custom storage backed is similar:
```python
class MyStorage(Storage):
    def read(self, path, deadline: datetime.datetime) -> bytes:
        """Read the file at the given path and return its contents as bytes.
        If the file does not exist, raise FileNotFoundError. If the file is
        older than the given deadline, raise CacheExpired.
        """
        ...

    def write(self, path, data: bytes) -> None:
        """Write the file at the given path."""
        ...

cache = Cache(storage=MyStorage())
```
You can also derive your storage class from `perscache.storage.FileStorage` if you are building a filesystem-based storage back-end. Refer to the [storage.py](/perscache/storage.py#FileStorage) file for more information.
