"""Support code shared by the Nuitka compiler benchmarks.

The benchmarks measure the pure Python parts of Nuitka, that is the front-end
that turns Python source code into a Nuitka node tree, and the optimization
passes that are then run on that tree. No C compiler and no Scons build is
involved, so the measurements are stable and only cover Nuitka code.

Nuitka is normally driven from the command line, therefore the compiler state
has to be brought up the same way that "nuitka.__main__" does it, before any
of the compiler modules can be used.
"""

import os
import sys

BENCHMARK_DIR = os.path.dirname(os.path.abspath(__file__))
CASES_DIR = os.path.join(BENCHMARK_DIR, "cases")

# Use the Nuitka of this checkout, not one that might be installed.
sys.path.insert(0, os.path.dirname(BENCHMARK_DIR))

# Source files used as compiler input, the benchmarks run for each of them.
CASE_NAMES = ("functions_and_calls", "classes_and_imports", "control_flow")

# Safety net, the optimization of the benchmark inputs settles in far fewer
# passes than this.
MAX_OPTIMIZATION_PASSES = 10


def _setupCompiler():
    """Bring the Nuitka compiler state up, like the command line would do."""

    os.environ["NUITKA_UPDATE_CHECK"] = "never"

    old_argv = sys.argv
    sys.argv = [
        "nuitka",
        "--module",
        "--quiet",
        "--no-progressbar",
        os.path.join(CASES_DIR, CASE_NAMES[0] + ".py"),
    ]

    try:
        import nuitka
        import nuitka.__main__ as nuitka_main

        # This lives in the "__main__" module of the Nuitka package and the
        # compiler expects to find it under this name.
        nuitka.getLaunchingNuitkaProcessEnvironmentValue = (
            nuitka_main.getLaunchingNuitkaProcessEnvironmentValue
        )

        from nuitka.options import Options
        from nuitka.plugins.Plugins import activatePlugins, setupHooks

        setupHooks()
        Options.parseArgs()
        activatePlugins()

        from nuitka.importing.Importing import setupImportingFromOptions
        from nuitka.plugins.Hooks import (
            onBeforeCodeParsing,
            onCompilationStartChecks,
        )

        onCompilationStartChecks()
        onBeforeCodeParsing()
        setupImportingFromOptions()
    finally:
        sys.argv = old_argv


_setupCompiler()

# These imports need the compiler state from above, so they cannot be done at
# the top of the module.
# isort:start

import nuitka.optimizations.Optimization as Optimization  # isort:skip
from nuitka.ModuleRegistry import addRootModule  # isort:skip
from nuitka.nodes.LocalsScopes import locals_dict_handles  # isort:skip
from nuitka.nodes.ModuleNodes import CompiledPythonModule  # isort:skip
from nuitka.optimizations.Tags import TagSet  # isort:skip
from nuitka.optimizations.TraceCollections import (  # isort:skip
    withChangeIndicationsTo,
)
from nuitka.SourceCodeReferences import (  # isort:skip
    makeSourceReferenceFromFilename,
)
from nuitka.tree.Building import createModuleTree  # isort:skip
from nuitka.tree.TreeHelpers import parseSourceCodeToAst  # isort:skip
from nuitka.utils.ModuleNames import ModuleName  # isort:skip

# Re-exported for the benchmark modules, which must not import Nuitka code
# before the compiler state is set up.
__all__ = [
    "CASE_NAMES",
    "ModuleName",
    "buildModuleTree",
    "getCaseSource",
    "optimizeModuleTree",
    "parseToAst",
]


def _makeHostModule():
    """Provide the top module that owns the internal helper functions.

    Some Python constructs are re-formulated into calls of helper functions
    that the compiler creates on demand and attaches to the top module, so
    there has to be one.
    """

    host_module = CompiledPythonModule(
        module_name=ModuleName("benchmark_host"),
        reason="benchmark",
        is_top=True,
        mode="compiled",
        future_spec=None,
        source_ref=makeSourceReferenceFromFilename(
            os.path.join(BENCHMARK_DIR, "bench_support.py")
        ),
    )

    addRootModule(host_module)

    return host_module


HOST_MODULE = _makeHostModule()


def getCaseSource(case_name):
    """Give filename and source code of a benchmark input module."""

    filename = os.path.join(CASES_DIR, case_name + ".py")

    with open(filename) as source_file:
        return filename, source_file.read()


def parseToAst(source_code, filename, module_name):
    """Parse source code to a CPython "ast" tree, the way Nuitka does it."""

    return parseSourceCodeToAst(
        source_code=source_code,
        module_name=ModuleName(module_name),
        filename=filename,
        line_offset=0,
    )


def buildModuleTree(source_code, filename, module_name):
    """Create the Nuitka node tree for the given source code.

    This is the whole front-end work for a single module, i.e. parsing,
    re-formulation of the Python constructs into the node tree, and taking
    variable closures.
    """

    # The handles are registered globally by the compiler, and duplicates are
    # rejected, so previous runs of the benchmark have to be forgotten.
    locals_dict_handles.clear()

    ast_tree = parseToAst(
        source_code=source_code, filename=filename, module_name=module_name
    )

    source_ref = makeSourceReferenceFromFilename(filename)

    module = CompiledPythonModule(
        module_name=ModuleName(module_name),
        reason="benchmark",
        is_top=False,
        mode="compiled",
        future_spec=None,
        source_ref=source_ref,
    )

    createModuleTree(
        module=module,
        source_ref=source_ref,
        ast_tree=ast_tree,
        is_main=False,
    )

    return module


def optimizeModuleTree(module):
    """Run module local optimization until no more changes are made.

    This is what "nuitka.optimizations.Optimization" does per module, without
    the parts that recurse into other modules.
    """

    Optimization.tag_set = TagSet()

    for _count in range(MAX_OPTIMIZATION_PASSES):
        Optimization.tag_set.clear()

        with withChangeIndicationsTo(Optimization.signalChange):
            module.computeModule()

        if not Optimization.tag_set:
            break

    return module
