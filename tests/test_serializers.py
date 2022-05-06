import pandas as pd
import pytest
from perscache import Cache
from perscache.compatibility import DATA_TYPES, DATAFRAMES, EXCLUSIONS
from perscache.serializers import (
    CloudPickleSerializer,
    CSVSerializer,
    JSONSerializer,
    ParquetSerializer,
    PickleSerializer,
    YAMLSerializer,
)
from perscache.storage import LocalFileStorage

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


@pytest.mark.parametrize("data", DATA_TYPES.items(), ids=DATA_TYPES.keys())
def test_data(cache, data):

    key, value = data
    counter = 0

    @cache.cache()
    def get_data():
        nonlocal counter
        counter += 1
        return value

    def assert_identical():
        if key in DATAFRAMES:
            df1: pd.DataFrame = get_data()
            df2: pd.DataFrame = get_data()
            assert df1.equals(df2)
        else:
            assert get_data() == get_data()

    if key in EXCLUSIONS[type(cache.serializer)]:
        with pytest.raises(Exception):
            assert_identical()
    else:
        assert_identical()
        assert counter == 1
