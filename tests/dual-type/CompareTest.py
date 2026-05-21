#     Copyright 2026, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file

# nuitka-project: --experimental=optimize-dual-int

from __future__ import print_function

# Large integers exceeding C long range, forcing NILONG dual-type path
a = 10**100
b = 10**50
c = -(10**100)
d = -(10**50)

# Equality
print(a == a)
print(a == b)
print(a == c)
print(c == d)
print(a == (10**100))
print(a != b)
print(a != a)

# Ordering
print(a > b)
print(a < b)
print(a >= b)
print(a <= b)
print(b > a)
print(b < a)

# With negatives
print(c < d)
print(c > d)
print(c < a)
print(a > c)
print(c >= d)
print(c <= d)

# Compare with zero
print(a > 0)
print(a < 0)
print(c > 0)
print(c < 0)
print(0 < a)
print(0 > c)

# Compare with small ints
print(a > 1)
print(a < 1)
print(a == 1)
print(1 < a)
print(1 > a)
print(1 == a)

# Compare equal values, different NILONG internal paths
x = 10**100
y = 10**100
print(x == y)
print(x == a)

# Comparison of negative and positive with small ints
print(c < (-1))
print(c > (-1))
print(c == (-1))
