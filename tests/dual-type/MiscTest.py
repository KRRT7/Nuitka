#     Copyright 2026, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file

# nuitka-project: --experimental=optimize-dual-int

from __future__ import print_function

# Large integers
a = 10**100
b = 10**50

# Unary negation of NILONG values
print(-a)
print(-(-a))
print(-b)
print(-(10**100))

# Unary plus (no-op but exercises NILONG path)
print(+a)
print(+b)

# Absolute value (indirectly exercises dual-type compare)
print(abs(a))
print(abs(-a))
print(abs(b))
print(abs(-b))

# Conversion to int (should be identity for NILONG)
print(int(a))
print(int(b))
print(int(-a))

# Multiplication (falls through to Python objects)
print(a * b)
print(a * 1)
print(1 * a)
print(a * 0)
print(0 * a)
