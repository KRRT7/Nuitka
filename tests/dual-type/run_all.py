#!/usr/bin/env python
#     Copyright 2026, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file


"""Runner for dual-type (NILONG) basic correctness tests.

Exercises the NILONG tagged-union dual-type implementations for
ADD, SUB, comparisons, and overflow under --experimental=optimize-dual-int.

"""

import os
import sys

# Find nuitka package relative to us.
sys.path.insert(
    0,
    os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
    ),
)

# isort:start

from nuitka.tools.testing.Common import (
    compareWithCPython,
    createSearchMode,
    scanDirectoryForTestCases,
    setup,
)


def main():
    python_version = setup(suite="dual-type", needs_io_encoding=True)

    search_mode = createSearchMode()

    for filename in scanDirectoryForTestCases("."):
        extra_flags = [
            "expect_success",
            "remove_output",
            "--file-reference-choice=original",
            "cpython_cache",
            "timing",
            "plugin_enable:pylint-warnings",
        ]

        active = search_mode.consider(dirname=None, filename=filename)

        if active:
            compareWithCPython(
                dirname=None,
                filename=filename,
                extra_flags=extra_flags,
                search_mode=search_mode,
            )

    search_mode.finish()


if __name__ == "__main__":
    main()

#     Python test originally created or extracted from other peoples work. The
#     parts from me are licensed as below. It is at least Free Software where
#     it's copied from other people. In these cases, that will normally be
#     indicated.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
