# perscache

![](https://img.shields.io/pypi/dm/perscache.svg?maxAge=2592000)
![](https://img.shields.io/pypi/v/perscache.svg?maxAge=2592000)
![](https://img.shields.io/pypi/l/perscache.svg?maxAge=2592000)

An easy to use decorator for persistent memoization: like `functools.lrucache`, but results persist between runs and can be stored in any format to any storage.

## Use cases
- Cache the results of a function that uses a lot of resources: runs for a long time, consumes a lot of traffic, uses up paid API calls etc.
- Speed up retreival of data that doesn't change often.
- Inspect the results of a decorated function while debugging.

## Features
- Async functions supported (unlike in `joblib`).
- Automatic cache invalidation when the decorated function arguments or code have been changed.
- You can set to ignore changes in certain arguments of the decorated function.
- Various serialization formats: JSON, YAML, pickle, Parquet, CSV etc.
- Various storage backends:
    - local disk (_implemented_) or
    - cloud storage (_to be implemented soon_).
- You can set default serialization format and storage backend and then change them on a per-function basis.
- You can easily add new serialization formats and storage back-ends.
- Serialization and storage are separated into two different classes, so that you can mix various serialization formats and storage back-ends as you like - JSON to local storage, Pickle to AWS, Parquet to Google Cloud Storage etc.
- Local storage is file-based, so you can easily inspect cached results.
- Easy to swap out the storage back-end when switching environments.
- Automatic cleanup: results can be
    - removed from storage when the total storage size exceeds a given threshold (_implemented_) or
    - limited to one result per function (_to be implemented soon_)

## Installation
```bash
pip install perscache
```

## Examples
### Basic usage
```python
from perscache import Cache

cache = Cache()

counter = 0

@cache.cache()
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
@cache.cache()
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

@cache.cache()
def get_data(key):
    print("This function has been changed...")
    return key

print(get_data("abc"))  # the function has been called again
# This function has been changed...
# abc

```
### Ignoring certain arguments
By specifying the arguments that should be ignored, you can still use the cache even in the values of these arguments have changed. **NOTE** that the decorated function should be called with ignored arguments specified as keyword arguments.
```python
@cache.cache(ignore=["ignore_this"])
def get_data(key, ignore_this):
    print("The function has been called...")
    return key

print(get_data("abc", ignore_this="ignore_1"))  # the function has been called
# The function has been called...
# abc

# using the cache although the the second argument is different
print(get_data("abc", ignore_this="ignore_2"))
# abc
```

### Changing the default serialization format and storage backend
```python
# set up serialization format and storage backend
cache = Cache(serializer=JSONSerializer(), storage=GCPStorage("bucket"))

...

# change the default serialization format
@cache.cache(serialization=PickleSerializer())
def get_data(key):
    ...
```

### Inspect cached results
When using `LocalFileStorage(location=...)`, the files are put into the directory specified by the `location` parameter.

The files are named like `<function_name>-<hash>.<serializer_extension>`, e.g. `get_data-9bf10a401d3d785317b2b35bcb5be1f2.json`.

### Automatic cleanup
When using `LocalFileStorage(max_size=...)`, the least recently used cache entries are automatically removed to keep the total cache size with the `max_size` limit.

### Make your own serialization and storage backends
To do this, you should:
1. Derive your own serialization or storage classes from the abstract `Serializer` and `Storage` classes and override the abstract methods. For the serialization classes, you should also provide the `extension` class variable that specifies the file extension.
2. Use your serialization or storage classes with the `Cache` class.

```python
class MySerializer(Serializer):

    extension = "data"

    def dumps(self, data):
        ...

    def loads(self, data):
        ...

class MyStorage(Storage):
    def read(self, filename):
        ...

    def write(self, filename, data):
        ...

cache = Cache(serializer=MySerializer(), storage=MyStorage())
```
