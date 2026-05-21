#     Copyright 2026, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file

# nuitka-project: --experimental=optimize-dual-int

from __future__ import print_function

# Large integers exceeding C long range, forcing NILONG dual-type path
a = 10**100
b = 10**50

# BINARY_OPERATION_SUB_NILONG_NILONG_NILONG
print(a - b)
print(b - a)

# Negative large integers
c = -(10**100)
d = -(10**50)
print(c - d)
print(d - c)
print(a - c)

# BINARY_OPERATION_SUB_NILONG_NILONG_DIGIT
print(a - 1)
print(a - (-1))
print(c - 1)
print(c - (-1))

# BINARY_OPERATION_SUB_NILONG_DIGIT_NILONG
print(1 - a)
print((-1) - a)
print(1 - c)
print((-1) - c)

# Zero subtraction
print(a - 0)
print(0 - a)
print(c - 0)
print(0 - c)

# Values that fit in C long
small = 42
large = 10**100
print(small - large)
print(large - small)

# Self subtraction
print(a - a)
print(b - b)
print(c - c)
