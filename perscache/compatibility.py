import collections
import datetime as dt

import pandas as pd

from .serializers import (CloudPickleSerializer, CSVSerializer, JSONSerializer,
                          ParquetSerializer, PickleSerializer, YAMLSerializer)

# data type samples

DATA_TYPES = {
    # NON-DATAFRAMES
    "str": "abc",
    "num": 123,
    "bool": True,
    "datetime": dt.datetime.now(),
    "datetime_with_timezone": dt.datetime.now(dt.timezone.utc),
    "list": [1, 2, 3],
    "set": {1, 2, 3},
    "dict": {"a": 1, "b": 2, "c": 3},
    "tuple": (1, 2, 3),
    "object": collections.namedtuple("NamedTuple", ["a", "b", "c"])(1, 2, 3),

    # DATAFRAMES
    "dataframe_no_dates": pd.DataFrame(
        {
            "a": [1, 2, 3],
            "b": ["A", "B", "C"],
        }
    ),
    "dataframe_with_dates": pd.DataFrame(
        {
            "a": [1, 2, 3],
            "b": ["A", "B", "C"],
            "c": [dt.datetime.now()] * 3,
        }
    ),
}

NON_DATAFRAMES = {
    "str",
    "num",
    "bool",
    "datetime",
    "datetime_with_timezone",
    "list",
    "set",
    "dict",
    "tuple",
    "object",
}

DATAFRAMES = {"dataframe_no_dates", "dataframe_with_dates"}


# Serializer exclusions:
# These serializers will not work with the mentioned data types --
# they will either raise an exception or the saved and loaded data
# will not be identical.

EXCLUSIONS = {
    # human-readable
    JSONSerializer: {
        "datetime",
        "datetime_with_timezone",
        "set",
        "tuple",
        "object",
    }
    | DATAFRAMES,
    YAMLSerializer: {"tuple", "object"} | DATAFRAMES,
    CSVSerializer: NON_DATAFRAMES | {"dataframe_with_dates"},

    # binary
    CloudPickleSerializer: {},
    PickleSerializer: {"object"},
    ParquetSerializer: NON_DATAFRAMES,
}
