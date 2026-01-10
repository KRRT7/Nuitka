#     Copyright 2025, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file


"""Standard plug-in to provide embedded terminal for macOS app bundles.

When building console/TUI applications with --mode=app on macOS, the resulting
.app bundles don't have a TTY when launched from Finder. This plugin injects
code that detects this situation and launches an embedded terminal window.
"""

import os

from nuitka.options.Options import (
    shallCreateAppBundle,
    shallUseMacOSEmbeddedTerminal,
)
from nuitka.plugins.PluginBase import NuitkaPluginBase
from nuitka.utils.FileOperations import getFileContents
from nuitka.utils.ModuleNames import ModuleName
from nuitka.utils.Utils import isMacOS


class NuitkaPluginEmbeddedTerminal(NuitkaPluginBase):
    """Provide embedded terminal for macOS app bundles.

    When a Nuitka-compiled macOS app bundle is launched from Finder without
    a TTY, this plugin enables the app to open its own terminal window using
    native Cocoa APIs via ctypes and re-execute itself with proper PTY handles.
    """

    plugin_name = "embedded-terminal"
    plugin_desc = (
        "Embedded terminal for macOS app bundles (--macos-app-console-mode=embedded)."
    )
    plugin_category = "macos-support"

    @classmethod
    def isRelevant(cls):
        # Only relevant for macOS app bundles with embedded console mode
        return isMacOS() and shallCreateAppBundle() and shallUseMacOSEmbeddedTerminal()

    @staticmethod
    def isAlwaysEnabled():
        return True

    def createFakeModuleDependency(self, module):
        """Create the embedded terminal module as a fake dependency."""
        full_name = module.getFullName()

        # Only create when __main__ is encountered
        if full_name != "__main__":
            return

        self.info("Creating embedded terminal module for macOS app bundle.")

        # Read the embedded terminal source
        source_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "utils", "EmbeddedTerminal.py"
        )

        try:
            source_code = getFileContents(source_path)
        except OSError:
            self.sysexit(
                "Error: Could not read EmbeddedTerminal.py from '%s'" % source_path
            )
            return

        yield (
            ModuleName("_nuitka_embedded_terminal"),
            source_code,
            source_path,
            "Embedded terminal for macOS app bundles",
        )

    @staticmethod
    def createPreModuleLoadCode(module):
        """Inject startup check for embedded terminal."""
        full_name = module.getFullName()

        if full_name != "__main__":
            return

        yield (
            """\
import sys, os
# Check if we need to launch embedded terminal (macOS app bundle without TTY)
if sys.platform == "darwin" and not sys.stdin.isatty():
    if not os.environ.get("NUITKA_EMBEDDED_TERMINAL"):
        from _nuitka_embedded_terminal import launch_embedded_terminal
        # Use sys.argv[0] as it contains the actual binary path in compiled apps
        binary_path = os.path.abspath(sys.argv[0])
        launch_embedded_terminal(binary_path, sys.argv)
        sys.exit(0)
""",
            "Embedded terminal startup check for macOS app bundles.",
        )


#     Part of "Nuitka", an optimizing Python compiler that is compatible and
#     integrates with CPython, but also works on its own.
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
