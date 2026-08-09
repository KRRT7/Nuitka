#     Copyright 2026, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file


""" Argument forms of "range" in for loops.

A for loop over the "range" built-in is specialized while building the tree,
and that may only happen for the argument forms it really is able to stand in
for. This module deliberately does not bind the name "range" anywhere, so that
the specialization is actually applied here.
"""

from __future__ import print_function

import sys


def loopOneArgument(count):
    result = []

    for value in range(count):
        result.append(value)

    return result


def loopTwoArguments(low, high):
    result = []

    for value in range(low, high):
        result.append(value)

    return result


def loopThreeArguments(low, high, step):
    result = []

    for value in range(low, high, step):
        result.append(value)

    return result


def loopStarArguments(args):
    result = []

    for value in range(*args):
        result.append(value)

    return result


def loopKeywordArgument():
    # Not a valid call, the specialization must not swallow the keyword and
    # loop over "range(1, 2)" instead.
    for value in range(1, 2, foo=3):
        print("must not get here", value)


count = len(sys.argv) + 2

print("One argument:", loopOneArgument(count))
print("Two arguments:", loopTwoArguments(1, count))
print("Three arguments:", loopThreeArguments(0, 2 * count, 2))
print("Star arguments:", loopStarArguments((1, count)))

try:
    loopKeywordArgument()
except TypeError:
    print("Keyword argument: TypeError")
else:
    print("Keyword argument: no exception, which is wrong")

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
