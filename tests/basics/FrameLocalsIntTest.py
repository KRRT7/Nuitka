#     Copyright 2026, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file


""" Frame locals containing dual int values.

Integer locals can be picked to use the "nuitka_ilong" C type, and are then
stored in frame locals storage as their object value only. Every frame locals
walker has to step over them by that size, or else all locals coming after one
are read from a wrong offset.

The walker is only reached for a frame that had its locals attached, which
happens when an exception leaves that frame, and then only through the
"f_locals" attribute of the traceback frame. An in-function "locals()" call is
built directly and does not go through the frame at all, and a live frame from
"sys._getframe()" has no locals attached yet.
"""

from __future__ import print_function

import sys


def displayFrameLocals(frame, names):
    frame_locals = frame.f_locals

    return [(name, frame_locals.get(name, "<missing>")) for name in names]


def failing():
    raise TypeError("frame locals check")


def findFrame(traceback, name):
    while traceback is not None:
        if traceback.tb_frame.f_code.co_name == name:
            return traceback.tb_frame

        traceback = traceback.tb_next

    return None


def raisingAfterIntLoop(count):
    # The loop makes "total" and "value" integer locals, and the ones after
    # them are read from a wrong offset if their size is mistaken.
    total = 0

    for value in range(count):
        total += value

    # Not a constant, or else this need not be a frame local at all.
    name = "after_int_loop_%d" % count
    values = [1, 2, 3]

    failing()

    # Keeps all of them live across the raising call.
    return total, value, name, values


def raisingAfterLargeInt(count, start):
    # Outside of the C long range, so the value has to stay object backed.
    total = start

    for value in range(count):
        total += value

    name = "after_large_int_%d" % count
    values = [4, 5, 6]

    failing()

    return total, value, name, values


_checked_names = ("count", "total", "value", "name", "values")


def checkFrameLocals(function, *args):
    try:
        function(*args)
    except TypeError:
        frame = findFrame(sys.exc_info()[2], function.__name__)

        return displayFrameLocals(frame, _checked_names)


print(
    "Frame locals after an int loop:",
    checkFrameLocals(raisingAfterIntLoop, 5),
)

print(
    "Frame locals with a large int:",
    checkFrameLocals(raisingAfterLargeInt, 5, 2**64),
)

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
