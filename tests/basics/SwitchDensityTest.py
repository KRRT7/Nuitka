import sys


def dense(value):
    match value:
        case 1:
            return "one"
        case 2:
            return "two"
        case 3:
            return "three"
        case 4:
            return "four"
        case _:
            return "other"


def sparse(value):
    match value:
        case -9223372036854775808:
            return "minimum"
        case 9223372036854775807:
            return "maximum"
        case _:
            return "other"


# Keep the input runtime-dependent so code generation cannot fold dispatch away.
value = len(sys.argv) + 2
print(dense(value))
print(sparse(value))
