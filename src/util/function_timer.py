import time
from .logger import Logger

class FunctionTimer:

    def timed_function(self, func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            execution_time = end_time - start_time
            # Logger().debug(f"Function {func.__name__} took {execution_time:.4f} seconds")
            return result
        return wrapper