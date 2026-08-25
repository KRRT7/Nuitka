"""Configuration for the Nuitka compiler benchmarks.

Importing the support module sets the Nuitka compiler state up, and it has to
happen before the benchmark modules are imported, which "conftest.py" makes
sure of.
"""

import bench_support  # isort:skip pylint: disable=unused-import
