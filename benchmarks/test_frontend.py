"""Benchmarks for the Nuitka compiler front-end.

These cover turning Python source code into a Nuitka node tree, which is what
Nuitka does before any optimization can happen.
"""

import pytest
from bench_support import (
    CASE_NAMES,
    buildModuleTree,
    getCaseSource,
    parseToAst,
)


@pytest.mark.parametrize("case_name", CASE_NAMES)
def test_parse_source_to_ast(benchmark, case_name):
    filename, source_code = getCaseSource(case_name)

    ast_tree = benchmark(
        parseToAst,
        source_code=source_code,
        filename=filename,
        module_name="benchmark_" + case_name,
    )

    assert ast_tree is not None


@pytest.mark.parametrize("case_name", CASE_NAMES)
def test_build_module_tree(benchmark, case_name):
    filename, source_code = getCaseSource(case_name)

    module = benchmark(
        buildModuleTree,
        source_code=source_code,
        filename=filename,
        module_name="benchmark_" + case_name,
    )

    assert module.subnode_body is not None


def test_build_module_tree_all_cases(benchmark):
    sources = [(case_name,) + getCaseSource(case_name) for case_name in CASE_NAMES]

    def buildAll():
        return [
            buildModuleTree(
                source_code=source_code,
                filename=filename,
                module_name="benchmark_all_" + case_name,
            )
            for case_name, filename, source_code in sources
        ]

    modules = benchmark(buildAll)

    assert len(modules) == len(CASE_NAMES)
