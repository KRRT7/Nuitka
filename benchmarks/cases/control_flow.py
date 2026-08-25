"""Benchmark input: loops, comprehensions and exception handling.

This module is never executed, it only serves as stable input for the Nuitka
compiler benchmarks. Do not change it without a good reason, changing it
changes the measured workload and makes historical comparisons invalid.
"""

import itertools

LIMIT = 128
TABLE = tuple(range(LIMIT))


def plain_loops(values):
    total = 0
    seen = []

    for value in values:
        if value % 2:
            total += value
        elif value % 3:
            total -= value
        else:
            continue

        seen.append(value)
    else:
        total += 1

    index = 0

    while index < len(seen):
        if seen[index] > LIMIT:
            break

        index += 1
    else:
        index = -1

    return total, index


def nested_loops(matrix):
    result = []

    for row in matrix:
        for column in row:
            for value in column:
                if value is None:
                    continue

                if value < 0:
                    break

                result.append(value)

    return result


def comprehensions(values):
    squares = [value * value for value in values if value]
    pairs = {value: value * 2 for value in values if value % 2}
    unique = {value % 7 for value in values}
    generated = (value + 1 for value in values if value > 3)
    nested = [[inner for inner in range(value)] for value in values[:8]]
    zipped = [(a, b) for a in values[:4] for b in values[:4] if a != b]

    return squares, pairs, unique, list(generated), nested, zipped


def exception_handling(value):
    try:
        result = TABLE[value]
    except IndexError:
        result = None
    except (TypeError, ValueError) as error:
        result = str(error)
    except Exception:
        raise
    else:
        result += 1
    finally:
        marker = True

    try:
        with open(str(value)) as input_file:
            for line in input_file:
                if line.startswith("#"):
                    continue

                result = line
    except IOError:
        result = ""

    return result, marker


def raising(value):
    if value < 0:
        raise ValueError("negative value %r" % value)

    if value == 0:
        raise TypeError("zero value")

    try:
        raise KeyError(value)
    except KeyError as error:
        raise RuntimeError("wrapped") from error


def context_managers(first, second):
    with first as a, second as b:
        result = a + b

    with first:
        with second:
            result += 1

    return result


def conditional_expressions(values):
    return [value if value % 2 else -value for value in values]


def boolean_logic(a, b, c):
    if a and b or not c:
        return a and b and c

    if a is not None and b is None:
        return a or b or c

    return (a or b) and (b or c)


def comparisons(a, b, c):
    chained = a < b < c
    mixed = a <= b != c
    identity = a is b is not c
    membership = a in TABLE and b not in TABLE

    return chained, mixed, identity, membership


def slicing(values):
    return (
        values[1:],
        values[:-1],
        values[1:-1],
        values[::2],
        values[::-1],
        values[1:10:3],
    )


def augmented_assignments(value):
    value += 1
    value -= 2
    value *= 3
    value //= 4
    value %= 5
    value **= 2
    value <<= 1
    value >>= 1
    value |= 8
    value &= 12
    value ^= 3

    return value


def generators_and_yields(values):
    def producer():
        for value in values:
            yield value

    def consumer():
        received = yield
        while received is not None:
            received = yield received * 2

    def delegating():
        yield from producer()
        yield from range(4)

    return list(delegating()), consumer


def itertools_usage(values):
    chained = list(itertools.chain(values, TABLE[:4]))
    grouped = [(key, list(group)) for key, group in itertools.groupby(sorted(values))]
    counted = list(itertools.islice(itertools.count(), 5))

    return chained, grouped, counted


def assertions(value):
    assert value is not None, "value must be given"
    assert isinstance(value, int)

    return value


def deletions(mapping, values):
    del mapping["key"]
    del values[0]
    del values[1:3]

    return mapping, values
