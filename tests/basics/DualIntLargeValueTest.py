#     Copyright 2026, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file


""" Dual int values that do not fit a C long.

An integer local can use the "nuitka_ilong" C type, which holds either a
"PyObject *", a C long, or both. When the object value is too large for a C
long, operations against a value that does have a C long go through the helpers
that decompose that C long into digits. Getting that decomposition wrong is not
visible for small values, because those take a shortcut that uses the C long
directly, so these all start out above the C long range.

Note that the large value has to be a constant for the local to be picked as a
dual int at all. Were it a parameter, its shape would not be known to be an
integer, and it would stay a plain object.
"""

from __future__ import print_function


def loopAddLarge(count):
    total = 2**64

    for value in range(count):
        total += value

    return total


def loopSubLarge(count):
    total = 2**64

    for value in range(count):
        total -= value

    return total


def loopAddNegativeLarge(count):
    total = -(2**64)

    for value in range(count):
        total += value

    return total


def loopSubNegativeLarge(count):
    total = -(2**64)

    for value in range(count):
        total -= value

    return total


def loopCompareLarge(count):
    total = 2**64
    results = []

    for value in range(count):
        results.append(
            (
                total == value,
                total != value,
                total < value,
                total <= value,
                total > value,
                total >= value,
            )
        )

        # Keep the value dual typed across the iterations.
        total += value

    return results


def loopCompareNegativeLarge(count):
    total = -(2**64)
    results = []

    for value in range(count):
        results.append(
            (
                total == value,
                total != value,
                total < value,
                total <= value,
                total > value,
                total >= value,
            )
        )

        total += value

    return results


def loopMultiDigit(count):
    # Well beyond a single C long, so more than one digit has to be decomposed.
    total = 2**96

    for value in range(count):
        total += value * 1000000007

    return total


def loopAcrossCLongBoundary(count):
    # Starts inside the C long range and crosses out of it.
    total = 2**63 - 2

    for value in range(count):
        total += value

    return total


print("Add to a large value:", loopAddLarge(5))
print("Subtract from a large value:", loopSubLarge(5))
print("Add to a negative large value:", loopAddNegativeLarge(5))
print("Subtract from a negative large value:", loopSubNegativeLarge(5))
print("Compare against a large value:", loopCompareLarge(3))
print("Compare against a negative large value:", loopCompareNegativeLarge(3))
print("Multi digit accumulation:", loopMultiDigit(5))
print("Across the C long boundary:", loopAcrossCLongBoundary(5))

#     Python tests originally created or extracted from other peoples work. The
#     parts were too small to be protected.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
