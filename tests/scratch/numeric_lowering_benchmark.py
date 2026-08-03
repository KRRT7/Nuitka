from time import perf_counter


def untyped_kernel(x0, y0, x1, y1, count):
    total = 0.0
    x_delta = x1 - x0
    y_delta = y1 - y0
    for index in range(count):
        x = x0 + index * x_delta
        y = y0 + index * y_delta
        total += x * x + y * y
    return total


def typed_kernel(x0: float, y0: float, x1: float, y1: float, count: int) -> float:
    total: float = 0.0
    x_delta: float = x1 - x0
    y_delta: float = y1 - y0
    for index in range(count):
        x: float = x0 + index * x_delta
        y: float = y0 + index * y_delta
        total += x * x + y * y
    return total


def measure(function, count):
    started = perf_counter()
    result = function(1.0, 2.0, 3.0, 4.0, count)
    return (perf_counter() - started) * 1000.0, result


def main():
    count = 200000
    for function in (untyped_kernel, typed_kernel):
        elapsed, result = measure(function, count)
        print("%s mean_ms=%.3f result=%.3f" % (function.__name__, elapsed, result))


if __name__ == "__main__":
    main()
