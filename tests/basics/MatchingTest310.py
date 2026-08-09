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
print(match_integer_only(10**100))
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


def match_overlapping_cases(value):
    match value:
        case 1 | 2:
            return "first"
        case 2 | 3:
            return "second"
        case _:
            return "other"


def match_integer_boundaries(value):
    match value:
        case -9223372036854775808:
            return "minimum"
        case 9223372036854775807:
            return "maximum"
        case _:
            return "other"


def match_integer_single_case(value):
    match value:
        case 42:
            return "answer"

    return "other"


def match_integer_dense(value):
    match value:
        case 1 | 2:
            return "low"
        case 3:
            return "three"
        case 4:
            return "four"

    return "other"


def if_integer_chain(value):
    if value == 1:
        return "one"
    elif value == 2:
        return "two"
    elif value == 3:
        return "three"
    else:
        return "other"


def if_duplicate_chain(value):
    if value == 4:
        return "first"
    elif value == 4:
        return "second"
    return "other"


def if_non_integer_chain(value):
    if value == 1.0:
        return "float"
    elif value == 2:
        return "integer"
    return "other"


def if_custom_equality(value):
    if value == 1:
        return "one"
    elif value == 2:
        return "two"
    return "other"


def if_constant_left_chain(value):
    if 1 == value:
        return "one"
    elif 2 == value:
        return "two"
    return "other"


def if_side_effectful_chain():
    calls = []

    def get_value():
        calls.append("called")
        return 2

    if get_value() == 1:
        result = "one"
    elif get_value() == 2:
        result = "two"
    else:
        result = "other"

    return result, len(calls)


def if_string_chain(value):
    if value == "alpha":
        return "alpha"
    elif value == "beta":
        return "beta"
    elif value == "gamma":
        return "gamma"
    return "other"


class StringSubclass(str):
    def __eq__(self, other):
        return other == "beta"


print(match_fallback(1))
print(match_fallback(1.0))
print(match_overlapping_cases(1))
print(match_overlapping_cases(2))
print(match_overlapping_cases(3))
print(match_integer_boundaries(-9223372036854775808))
print(match_integer_boundaries(9223372036854775807))
print(match_integer_single_case(42))
print(match_integer_single_case(41))
print(match_integer_dense(len(calls)))
print(if_integer_chain(1))
print(if_integer_chain(3))
print(if_integer_chain(4))
print(if_duplicate_chain(4))
print(if_non_integer_chain(1))
print(if_non_integer_chain(2))
print(if_custom_equality(EqualityValue()))
print(if_constant_left_chain(1))
print(if_constant_left_chain(3))
print(if_side_effectful_chain())
print(if_string_chain("alpha"))
print(if_string_chain("delta"))
print(if_string_chain(StringSubclass("not-beta")))
