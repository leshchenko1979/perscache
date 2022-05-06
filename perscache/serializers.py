from abc import ABC, abstractmethod
from typing import Any


class Serializer(ABC):

    extension: str = None

    @abstractmethod
    def dumps(self, data: Any) -> bytes:
        ...

    def loads(self, data: bytes) -> Any:
        ...


class CloudPickleSerializer(Serializer):

    extension = "pickle"

    def dumps(self, data: Any) -> bytes:
        import cloudpickle

        return cloudpickle.dumps(data)

    def loads(self, data: bytes) -> Any:
        import cloudpickle

        return cloudpickle.loads(data)


class JSONSerializer(Serializer):

    extension = "json"

    def dumps(self, data: Any) -> bytes:
        import json

        return json.dumps(data).encode("utf-8")

    def loads(self, data: bytes) -> Any:
        import json

        return json.loads(data.decode("utf-8"))


class PickleSerializer(Serializer):

    extension = "pickle"

    def dumps(self, data: Any) -> bytes:
        import pickle

        return pickle.dumps(data)

    def loads(self, data: bytes) -> Any:
        import pickle

        return pickle.loads(data)


class YAMLSerializer(Serializer):

    extension = "yaml"

    def dumps(self, data: Any) -> bytes:
        import yaml

        return yaml.dump(data).encode("utf-8")

    def loads(self, data: bytes) -> Any:
        import yaml

        return yaml.load(data.decode("utf-8"))


class ParquetSerializer(Serializer):

    extension = "parquet"

    def dumps(self, data: Any) -> bytes:
        import pyarrow
        import pyarrow.parquet

        return pyarrow.parquet.write_table(pyarrow.Table.from_pandas(data)).to_buffer()

    def loads(self, data: bytes) -> Any:
        import pyarrow
        import pyarrow.parquet

        return pyarrow.parquet.read_table(pyarrow.BufferReader(data)).to_pandas()


class CSVSerializer(Serializer):

    extension = "csv"

    def dumps(self, data: Any) -> bytes:
        import pandas as pd
        import io

        return pd.DataFrame(data).to_csv().encode("utf-8")

    def loads(self, data: bytes) -> Any:
        import pandas as pd
        import io

        return pd.read_csv(io.StringIO(data.decode("utf-8")))
