import time
import functools

from .logger import logger

def timing_it(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        logger.info(f"🔍 {func.__name__} 耗时: {end - start:.4f} 秒")
        return result
    return wrapper