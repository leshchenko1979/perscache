from logging import getLogger, DEBUG, NullHandler
import functools as ft

logger = getLogger("perscache")
logger.setLevel(DEBUG)
logger.addHandler(NullHandler())

debug = logger.debug

def trace(f):
    ft.wraps(f)
    def wrapper(func, *args, **kwargs):
        debug(f'Entering {f.__name__}, args={args}, kwargs={kwargs}')
        result = f(func, *args, **kwargs)
        debug(f'Exiting {f.__name__}, result={result}')
        return result

    return wrapper
