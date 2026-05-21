#     Copyright 2026, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file

# nuitka-project: --experimental=optimize-dual-int

from __future__ import print_function

# Overflow scenario: values fit in C long but combined operation overflows
# 2**62 is 4611686018427387904, fits in long (2**63-1 on 64-bit)
# Adding two 2**62 values gives 2**63 which exceeds LONG_MAX
e = 2**62
f = 2**62
print(e + f)

# Subtracting -2**62 from 2**62 gives 2**63 > LONG_MAX
g = 2**62
h = -(2**62)
print(g - h)

# Adding negative: -(2**62) + -(2**62) gives -(2**63) < LONG_MIN
print(h + h)

# Near boundaries
# LONG_MAX approx 2**63-1 = 9223372036854775807
# LONG_MIN approx -2**63 = -9223372036854775808
big_near_max = 2**63 - 1
print(big_near_max + 0)
print(big_near_max - 1)

near_min = -(2**63)
print(near_min + 1)
print(near_min - 1)
