#     Copyright 2026, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file


"""Setup file for Nuitka.

This applies a few tricks. First, the Nuitka version is read from
the source code. Second, the packages are scanned from the filesystem,
and third, the byte code compilation is avoided for inline copies of
scons with mismatching Python major versions. Also a binary distribution
is enforced, to avoid being cached with wrong inline copies for the
Python version.

spellchecker: ignore chdir,pythonw,tqdm,distutil,atomicwrites,markupsafe
spellchecker: ignore wininst,distclass,Containerfile,orderedset
"""

import os
import sys

os.chdir(os.path.dirname(__file__) or ".")
sys.path.insert(0, os.path.abspath(os.getcwd()))

# Disable setuptools warnings before importing it.
import warnings

warnings.filterwarnings("ignore", "")

# Don't allow importing this, and make recognizable that
# the above imports are not to follow. Sometimes code imports
# setup and then Nuitka ends up including itself.
if __name__ != "__main__":
    sys.exit("Cannot import 'setup' module of Nuitka")

# isort:start

import fnmatch

from setuptools import Distribution, setup

from nuitka.Version import getNuitkaVersion

version = getNuitkaVersion()


def findNuitkaPackages():
    result = []

    for root, dirnames, filenames in os.walk("nuitka"):
        # Packages must contain "__init__.py" or they are merely directories
        # in Nuitka as we are Python2 compatible.
        if "__init__.py" not in filenames:
            continue

        # The "release" namespace is code used to release, but not itself for
        # release, same goes for "quality".
        if "release" in dirnames:
            dirnames.remove("release")
        if "quality" in dirnames:
            dirnames.remove("quality")

        # Handled separately.
        if "inline_copy" in dirnames:
            dirnames.remove("inline_copy")

        result.append(root.replace(os.path.sep, "."))

    return result


inline_copy_files = []
no_byte_compile = []


def addDataFiles(files_list, base_path, do_byte_compile=True):
    patterns = (
        "%s/*.py" % base_path,
        "%s/*/*.py" % base_path,
        "%s/*/*/*.py" % base_path,
        "%s/*/*/*/*.py" % base_path,
        "%s/*/*/*/*/*.py" % base_path,
        "%s/config*" % base_path,
        "%s/LICENSE*" % base_path,
        "%s/*/LICENSE*" % base_path,
        "%s/READ*" % base_path,
    )

    files_list.extend(patterns)

    if not do_byte_compile:
        no_byte_compile.extend(patterns)


def addInlineCopy(name, do_byte_compile=True):
    if os.getenv("NUITKA_NO_INLINE_COPY", "0") == "1":
        return

    addDataFiles(
        inline_copy_files, "inline_copy/%s" % name, do_byte_compile=do_byte_compile
    )


sdist_mode = "sdist" in sys.argv
install_mode = "install" in sys.argv

addInlineCopy("appdirs")
if sys.version_info < (3, 5) or sdist_mode:
    addInlineCopy("glob2")
addInlineCopy("markupsafe")
addInlineCopy("tqdm")

addInlineCopy("stubgen")

if os.name == "nt" or sdist_mode:
    addInlineCopy("atomicwrites")
    addInlineCopy("clcache")
    addInlineCopy("colorama")

if (os.name == "nt" and sys.version_info >= (3, 6)) or sdist_mode:
    addInlineCopy("pefile")

if sys.version_info < (3,) or sdist_mode:
    addInlineCopy("pkg_resources_27", do_byte_compile=sys.version_info < (3,))
    addInlineCopy("yaml_27", do_byte_compile=sys.version_info < (3,))
if (3,) < sys.version_info < (3, 6) or sdist_mode:
    addInlineCopy("yaml_35", do_byte_compile=(3,) < sys.version_info < (3, 6))
if sys.version_info >= (3, 6) or sdist_mode:
    addInlineCopy("yaml", do_byte_compile=sys.version_info >= (3, 6))

if sys.version_info < (3, 6) or sdist_mode:
    addInlineCopy("jinja2_35", do_byte_compile=sys.version_info < (3, 6))
if sys.version_info >= (3, 6) or sdist_mode:
    addInlineCopy("jinja2", do_byte_compile=sys.version_info >= (3, 6))

addInlineCopy("pkg_resources")

# Scons really only, with historic naming and positioning. Needs to match the
# "scons.py" in bin with respect to versions selection.
addInlineCopy("bin")

# Needs to match the version dispatch in "nuitka/build/inline_copy/bin/scons.py".
# Scons may be executed with a different Python than the one used
# to install Nuitka, so include the supported inline copies regardless.
if os.name == "nt" or sdist_mode:
    addInlineCopy(
        "lib/scons-4.3.0",
        do_byte_compile=(3, 5) <= sys.version_info < (3, 7),
    )
if os.name == "nt" or sdist_mode:
    addInlineCopy("lib/scons-4.10.1", do_byte_compile=sys.version_info >= (3, 7))
if (os.name != "nt" and sys.version_info < (2, 7)) or sdist_mode:
    addInlineCopy("lib/scons-2.3.2", do_byte_compile=sys.version_info < (2, 7))
if (os.name != "nt" and sys.version_info >= (2, 7)) or sdist_mode:
    addInlineCopy(
        "lib/scons-3.1.2",
        do_byte_compile=os.name != "nt" and sys.version_info >= (2, 7),
    )

nuitka_packages = findNuitkaPackages()

# Include extra files
package_data = {
    "nuitka.build": inline_copy_files,
}


try:
    import distutils.util
except ImportError:
    # With Python 3.12 setuptools._distutils.util what we can use.
    try:
        import setuptools._distutils.util as distutils_util
    except ImportError:
        distutils_util = None
else:
    distutils_util = distutils.util

if distutils_util is not None:
    orig_byte_compile = distutils_util.byte_compile

    def byte_compile(py_files, *args, **kw):
        # Disable bytecode compilation output, too annoying.
        kw["verbose"] = 0

        # Avoid attempting files that won't work.
        py_files = [
            filename
            for filename in py_files
            if not any(
                fnmatch.fnmatch(filename, "*/*/*/" + pattern)
                for pattern in no_byte_compile
            )
        ]

        orig_byte_compile(py_files, *args, **kw)

    distutils_util.byte_compile = byte_compile


# With this, we can enforce a binary package.
class BinaryDistribution(Distribution):
    """Distribution which always forces a binary package with platform name"""

    @staticmethod
    def has_ext_modules():
        # For "python setup.py install" this triggers an attempt to lookup
        # package dependencies, which fails to work, since it's not yet
        # installed and might not yet be in PyPI as well.
        return not install_mode


setup(
    packages=nuitka_packages,
    package_data=package_data,
    # As we do version specific hacks for installed inline copies, make the
    # wheel version and platform specific.
    distclass=BinaryDistribution,
    verbose=0,
)

#     Part of "Nuitka", an optimizing Python compiler that is compatible and
#     integrates with CPython, but also works on its own.
#
#     Licensed under the GNU Affero General Public License, Version 3 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#        http://www.gnu.org/licenses/agpl.txt
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
