import io
import json
import pickle
from abc import ABC, abstractmethod
from typing import Any, Callable

import cloudpickle


class Serializer(ABC):

    extension: str = None

    def __repr__(self):
        return f"<{self.__class__.__name__}(extension='{self.extension}')>"

    @abstractmethod
    def dumps(self, data: Any) -> bytes:
        ...

    @abstractmethod
    def loads(self, data: bytes) -> Any:
        ...


def make_serializer(
    class_name: str,
    ext: str,
    dumps_fn: Callable[[Any], bytes],
    loads_fn: Callable[[bytes], Any],
) -> Serializer:
    """Create a serializer class.

    Args:
        class_name (str): The name of the serializer class.
        extension (str): The file extension of the serialized data.
        dumps (callable): The function to serialize data.
                Takes a single argument and returns a bytes object.
        loads (callable): The function to deserialize data.
                Takes a single bytes object as argument and returns an object.
    """

    class SerializerClass(Serializer):
        extension = ext
        dumps = lambda _, data: dumps_fn(data)
        loads = lambda _, data: loads_fn(data)

    SerializerClass.__name__ = class_name

    return SerializerClass


CloudPickleSerializer = make_serializer(
    "CloudPickleSerializer", "pickle", cloudpickle.dumps, cloudpickle.loads
)

JSONSerializer = make_serializer(
    "JSONSerializer",
    "json",
    lambda data: json.dumps(data).encode("utf-8"),
    lambda data: json.loads(data.decode("utf-8")),
)

PickleSerializer = make_serializer(
    "PickleSerializer", "pickle", pickle.dumps, pickle.loads
)


class YAMLSerializer(Serializer):

    extension = "yaml"

    def dumps(self, data: Any) -> bytes:
        import yaml

        return yaml.dump(data).encode("utf-8")

    def loads(self, data: bytes) -> Any:
        import yaml

        return yaml.safe_load(data.decode("utf-8"))


class ParquetSerializer(Serializer):
    """Serializes a Pandas DataFrame to a Parquet format with adjustable compression."""

    extension = "parquet"

    def __init__(self, compression: str = "brotli"):
        self.compression = compression

    def __repr__(self):
        return f"<ParquetSerializer(extentsion='parquet', compression='{self.compression}')>"

    def dumps(self, data: Any) -> bytes:
        import pyarrow
        import pyarrow.parquet

        buf = pyarrow.BufferOutputStream()
        pyarrow.parquet.write_table(
            pyarrow.Table.from_pandas(data), buf, compression=self.compression
        )
        buf.flush()
        return buf.getvalue()

    def loads(self, data: bytes) -> Any:
        import pyarrow
        import pyarrow.parquet

        return pyarrow.parquet.read_table(pyarrow.BufferReader(data)).to_pandas()


class CSVSerializer(Serializer):

    extension = "csv"

    def dumps(self, data: Any) -> bytes:
        import pandas as pd

        return pd.DataFrame(data).to_csv().encode("utf-8")

    def loads(self, data: bytes) -> Any:
        import pandas as pd

        return pd.read_csv(io.StringIO(data.decode("utf-8")), index_col=0)
