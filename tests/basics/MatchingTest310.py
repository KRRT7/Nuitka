#     Copyright 2026, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file


def match_integer(value):
    match value:
        case -2 | 0:
            return "small"
        case 7:
            return "seven"
        case 100:
            return "hundred"
        case _:
            return "other"


def match_integer_only(value):
    match value:
        case -2 | 0:
            return "small"
        case 7:
            return "seven"
        case 100:
            return "hundred"

    return "other"


class EqualityValue(object):
    def __eq__(self, other):
        return other == 7


class IntegerSubclass(int):
    def __eq__(self, other):
        return other == 99


calls = []


def get_value():
    calls.append("called")
    return 7


print(match_integer(0))
print(match_integer(7))
print(match_integer(1))
print(match_integer_only(-2))
print(match_integer_only(10 ** 100))
print(match_integer_only(1.0))
print(match_integer_only(True))
print(match_integer_only(False))
print(match_integer_only(EqualityValue()))
print(match_integer_only(IntegerSubclass(7)))
print(match_integer_only(get_value()))
print(len(calls))


def match_fallback(value):
    match value:
        case 1.0:
            return "float"
        case 1:
            return "integer"
        case _:
            return "other"


print(match_fallback(1))
print(match_fallback(1.0))

