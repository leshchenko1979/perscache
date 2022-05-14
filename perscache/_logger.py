from logging import getLogger, DEBUG, NullHandler
import functools as ft

logger = getLogger("perscache")
logger.setLevel(DEBUG)
logger.addHandler(NullHandler())

debug = logger.debug

MAX_LEN = 200


def _trim(s):
    return f"{str(s)[:MAX_LEN]}..." if len(str(s)) > MAX_LEN else s


def trace(f):
    @ft.wraps(f)
    def wrapper(*args, **kwargs):
        debug(
            f"Entering {_trim(f.__name__)}, args={_trim(args)}, kwargs={_trim(kwargs)}"
        )
        result = f(*args, **kwargs)
        debug(f"Exiting {_trim(f.__name__)}, result={_trim(result)}")
        return result

    return wrapper
