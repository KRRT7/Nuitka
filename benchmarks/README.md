# Nuitka compiler benchmarks

These benchmarks measure the compiler itself, i.e. the pure Python code of Nuitka, and not the
runtime performance of compiled programs, which the programs in `tests/benchmarks` are about.

They are run in CI with [CodSpeed](https://codspeed.io) in CPU simulation mode, so results are
hardware independent and small changes are visible.

## What is measured

- `test_frontend.py`: parsing source code to an `ast` tree and re-formulating it into a Nuitka node
  tree, including taking variable closures.
- `test_optimization.py`: the module local optimization passes that run on the node tree until it no
  longer changes.
- `test_compiler_utils.py`: utility code that is used all over the compiler, module names, ordered
  containers and C string encoding.

No C compiler, no Scons build and no import recursion into other modules is involved, so the
measurements only cover Nuitka code and are stable.

The input modules in `cases` are compiler input only, they are never executed. Changing them changes
the measured workload and makes comparisons with older results meaningless, so please leave them
alone unless a construct is missing.

## Running them locally

```bash
python -m pip install pytest-codspeed
python -m pytest benchmarks
```

That only checks that the benchmarks work. To also get measurements, use the
[CodSpeed CLI](https://codspeed.io/docs/cli):

```bash
codspeed run --mode simulation -- python -m pytest benchmarks --codspeed
```
