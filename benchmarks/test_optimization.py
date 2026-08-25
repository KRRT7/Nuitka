"""Benchmarks for the Nuitka optimization passes.

The node tree is built during the setup of each round, so that only the module
local optimization work is measured.
"""

import pytest
from bench_support import (
    CASE_NAMES,
    buildModuleTree,
    getCaseSource,
    optimizeModuleTree,
)


@pytest.mark.parametrize("case_name", CASE_NAMES)
def test_optimize_module(benchmark, case_name):
    filename, source_code = getCaseSource(case_name)

    def setup():
        module = buildModuleTree(
            source_code=source_code,
            filename=filename,
            module_name="benchmark_optimized_" + case_name,
        )

        return (module,), {}

    module = benchmark.pedantic(optimizeModuleTree, setup=setup)

    assert module.subnode_body is not None


@pytest.mark.parametrize("case_name", CASE_NAMES)
def test_build_and_optimize_module(benchmark, case_name):
    filename, source_code = getCaseSource(case_name)

    def compileModule():
        return optimizeModuleTree(
            buildModuleTree(
                source_code=source_code,
                filename=filename,
                module_name="benchmark_compiled_" + case_name,
            )
        )

    module = benchmark(compileModule)

    assert module.subnode_body is not None
