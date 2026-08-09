#     Copyright 2026, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file


""" Shadowing of the "range" built-in around for loops.

A for loop over "range" is specialized while building the tree already, which
happens before variable closures are done, so it cannot ask what the name will
refer to. It has to give that up for a module that binds the name anywhere.

Note that this whole module binds "range" in several ways, so none of the loops
in here may be treated as using the built-in.
"""

from __future__ import print_function


def loopOverLocalRange():
    def range(count):
        return ["local_%d" % value for value in (0, 1, 2)][:count]

    result = []

    for value in range(3):
        result.append(value)

    return result


def loopOverParameterRange(range):
    result = []

    for value in range(3):
        result.append(value)

    return result


def loopOverGlobalRange():
    result = []

    for value in range(3):
        result.append(value)

    return result


def loopWithStep():
    result = []

    for value in range(0, 6, 2):
        result.append(value)

    return result


print("Local shadowing:", loopOverLocalRange())
print("Parameter shadowing:", loopOverParameterRange(lambda count: ["par"] * count))
print("Step argument:", loopWithStep())

# Rebind the module level name, which makes the module bind "range" and must
# therefore prevent the built-in from being assumed anywhere in here.
_original_range = range


def range(count):
    return ["global_%d" % value for value in _original_range(count)]


print("Global shadowing:", loopOverGlobalRange())

range = _original_range

print("Restored:", loopOverGlobalRange())

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
