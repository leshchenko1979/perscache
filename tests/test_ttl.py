import datetime as dt
import time

from perscache import Cache


def test_ttl(tmp_path):
    cache = Cache()

    counter = 0

    @cache.cache(ttl=dt.timedelta(seconds=0.1))
    def get_data(key):
        nonlocal counter
        counter += 1
        return key

    get_data(1)
    assert counter == 1

    get_data(1)
    assert counter == 1

    get_data(2)
    assert counter == 2

    time.sleep(0.2)

    get_data(1)
    assert counter == 3

    get_data(2)
    assert counter == 4
