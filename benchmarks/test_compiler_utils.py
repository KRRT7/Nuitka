"""Benchmarks for utility code that is hot during a compilation.

Module names, ordered containers and C string encoding are used all over the
compiler and the code generation, so small changes there add up.
"""

from bench_support import ModuleName

from nuitka.containers.OrderedSets import OrderedSet, buildOrderedSet
from nuitka.utils.CStrings import (
    encodePythonIdentifierToC,
    encodePythonStringToC,
    encodePythonUnicodeToC,
)

MODULE_NAMES = (
    "os",
    "os.path",
    "sys",
    "collections.abc",
    "numpy.core._multiarray_umath",
    "PyQt5.QtCore",
    "django.db.models.fields.related",
    "scipy.sparse.linalg.eigen.arpack",
    "pkg_resources._vendor.jaraco.text",
    "nuitka.nodes.ExpressionBases",
)

SHELL_PATTERNS = ("os.*", "numpy.**", "*.QtCore", "django.db.models.*")

TEXT_VALUES = (
    "simple",
    "with spaces and 'quotes'",
    "tab\tand\nnewline",
    "unicode: \u00e4\u00f6\u00fc\u20ac",
    "a" * 200,
)

IDENTIFIERS = (
    "simple_name",
    "name.with.dots",
    "name-with-dashes",
    "\u00e4\u00f6\u00fc",
    "some$special%chars",
)


def test_module_name_operations(benchmark):
    def moduleNameOperations():
        result = []

        for name in MODULE_NAMES:
            module_name = ModuleName(name)

            result.append(
                (
                    module_name.getPackageName(),
                    module_name.getBasename(),
                    module_name.getTopLevelPackageName(),
                    tuple(module_name.getParentPackageNames()),
                    module_name.asPath(),
                    module_name.hasNamespace("os"),
                    module_name.getChildNamed("child"),
                )
            )

        return result

    assert len(benchmark(moduleNameOperations)) == len(MODULE_NAMES)


def test_module_name_pattern_matching(benchmark):
    module_names = tuple(ModuleName(name) for name in MODULE_NAMES)

    def matchPatterns():
        return [
            module_name.matchesToShellPatterns(SHELL_PATTERNS)
            for module_name in module_names
        ]

    assert len(benchmark(matchPatterns)) == len(module_names)


def test_ordered_set_operations(benchmark):
    values = tuple(range(512))

    def orderedSetOperations():
        result = OrderedSet()

        for value in values:
            result.add(value)

        for value in values[::2]:
            result.discard(value)

        merged = buildOrderedSet(result, values[:64], values[-64:])

        return len(merged), tuple(merged)[:8]

    assert benchmark(orderedSetOperations)[0] > 0


def test_c_string_encoding(benchmark):
    byte_values = tuple(value.encode("utf8") for value in TEXT_VALUES)

    def encodeConstants():
        result = []

        for value in byte_values:
            result.append(encodePythonStringToC(value))

        for value in TEXT_VALUES:
            result.append(encodePythonUnicodeToC(value))

        for value in IDENTIFIERS:
            result.append(encodePythonIdentifierToC(value))

        return result

    expected = len(TEXT_VALUES) * 2 + len(IDENTIFIERS)

    assert len(benchmark(encodeConstants)) == expected
