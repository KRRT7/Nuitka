"""Benchmark input: function definitions, calls and closures.

This module is never executed, it only serves as stable input for the Nuitka
compiler benchmarks. Do not change it without a good reason, changing it
changes the measured workload and makes historical comparisons invalid.
"""

import functools
import os
import sys

DEFAULT_TIMEOUT = 30
RETRY_DELAYS = (1, 2, 5, 10, 30)


def simple_add(a, b):
    return a + b


def with_defaults(a, b=1, c="text", d=None, e=(), f=DEFAULT_TIMEOUT):
    if d is None:
        d = {}

    return a, b, c, d, e, f


def with_star_args(first, *args, **kwargs):
    total = first

    for arg in args:
        total += arg

    for key in sorted(kwargs):
        total += kwargs[key]

    return total


def keyword_only(a, *, b, c=3):
    return a * b + c


def annotated(a: int, b: str = "x", *args: int, **kwargs: str) -> str:
    return b * a


def nested_definitions(value):
    def inner(other):
        def innermost():
            return value + other

        return innermost

    return inner(value)()


def closure_over_loop(values):
    result = []

    for value in values:

        def accessor(value=value):
            return value * 2

        result.append(accessor)

    return result


def recursive_walk(node, depth=0):
    if depth > 10:
        return 0

    count = 1

    for child in node:
        count += recursive_walk(child, depth + 1)

    return count


def call_chains(obj):
    return obj.first().second(1, 2).third(x=1, y=2).fourth(*[1, 2], **{"z": 3})


def conditional_calls(flag, value):
    if flag:
        result = simple_add(value, 1)
    elif value > 10:
        result = with_defaults(value, b=2)
    else:
        result = with_star_args(value, 1, 2, 3, x=4)

    return result


def default_evaluation(a=os.sep, b=sys.maxsize, c=len("abc")):
    return a, b, c


def memoized(function):
    cache = {}

    @functools.wraps(function)
    def wrapper(*args):
        if args not in cache:
            cache[args] = function(*args)

        return cache[args]

    return wrapper


@memoized
def fibonacci(n):
    if n < 2:
        return n

    return fibonacci(n - 1) + fibonacci(n - 2)


def lambda_usage(values):
    doubled = list(map(lambda value: value * 2, values))
    filtered = list(filter(lambda value: value % 3, doubled))
    combined = sorted(filtered, key=lambda value: (value % 7, value))

    return combined


def unpacking(values):
    first, second, *rest = values
    (a, b), c = values[:2], values[2]

    return first, second, rest, a, b, c


def multiple_returns(value):
    if value < 0:
        return "negative"

    if value == 0:
        return "zero"

    if value < 10:
        return "small"

    return "large"


def string_formatting(name, count):
    old_style = "%s has %d items" % (name, count)
    new_style = "{0} has {1} items".format(name, count)
    formatted = f"{name} has {count} items"

    return old_style, new_style, formatted


def generator_function(limit):
    total = 0

    for value in range(limit):
        total += value
        yield total

    return total


def apply_all(functions, value):
    for function in functions:
        value = function(value)

    return value


def retry(function, delays=RETRY_DELAYS):
    for delay in delays:
        try:
            return function()
        except ValueError:
            continue

    raise ValueError(function)
