from machine import Timer

def periodic(freq):
    def decorator(func):
        t = Timer()
        t.init(freq=freq, mode=Timer.PERIODIC, callback=func)
        return func
    return decorator

def logger():
    def decorator(func):
        def wrapper(*args, **kwargs):
            print("--------------------------------")
            print(f"Function '{func.__name__}' called")
            data = func(*args, **kwargs)
            print(f"It returned: {data}")
            return data
        return wrapper
    return decorator