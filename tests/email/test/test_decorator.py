from functools import wraps
import time

def log_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__} with args: {args} and kwargs: {kwargs}")
        return func(*args, **kwargs)
    return wrapper

@log_call
def test_add():
    pass

def tick_total(func):
    @wraps(func)
    def wrapper():
        tick_total = time.time()
        print("Starting...")
        func()
        tick_total = time.time() - tick_total
        print(f"Total time: {tick_total}")
    return wrapper

@tick_total
def dothis():
    print("11111111111")
    time.sleep(1)
    print("222222222222")

@tick_total
def dothat():
    time.sleep(2)

def test_dothis():
    dothis()