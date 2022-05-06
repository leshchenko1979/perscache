from calendar import c
import pytest
from perscache import Cache
from perscache.serializers import (
    CSVSerializer,
    CloudPickleSerializer,
    JSONSerializer,
    ParquetSerializer,
    PickleSerializer,
    YAMLSerializer,
)
from perscache.storage import LocalFileStorage

import datetime as dt
import collections
import pandas as pd

SERIALIZERS = {
    # human-readable
    "json": JSONSerializer,
    "yaml": YAMLSerializer,
    "csv": CSVSerializer,

    # binary
    "cloudpickle": CloudPickleSerializer,
    "pickle": PickleSerializer,
    "parquet": ParquetSerializer,
}


@pytest.fixture(params=SERIALIZERS.values(), ids=SERIALIZERS.keys())
def cache(tmp_path, request):
    return Cache(serializer=request.param(), storage=LocalFileStorage(tmp_path))


DATA = {
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

EXCLUSIONS = {
    # human-readable
    JSONSerializer: {
        "datetime",
        "datetime_with_timezone",
        "set",
        "tuple",
        "object",
    } | DATAFRAMES,
    YAMLSerializer: {"tuple", "object"} | DATAFRAMES,
    CSVSerializer: NON_DATAFRAMES | {"dataframe_with_dates"},

    # binary
    CloudPickleSerializer: {},
    PickleSerializer: {"object"},
    ParquetSerializer: NON_DATAFRAMES,
}


@pytest.mark.parametrize("data", DATA.items(), ids=DATA.keys())
def test_data(cache, data):

    key, value = data
    counter = 0

    @cache.cache()
    def get_data():
        nonlocal counter
        counter += 1
        return value

    def assert_identical():
        if key in NON_DATAFRAMES:
            assert get_data() == get_data()
        else:
            df1: pd.DataFrame = get_data()
            df2: pd.DataFrame = get_data()
            assert df1.equals(df2)

    if key in EXCLUSIONS[type(cache.serializer)]:
        with pytest.raises(Exception):
            assert_identical()
    else:
        assert_identical()
        assert counter == 1
