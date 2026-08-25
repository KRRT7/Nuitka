"""Benchmark input: classes, inheritance and import variants.

This module is never executed, it only serves as stable input for the Nuitka
compiler benchmarks. Do not change it without a good reason, changing it
changes the measured workload and makes historical comparisons invalid.
"""

import collections
import os
import os.path
import sys
from collections import OrderedDict, defaultdict
from os.path import basename, dirname, join

MODULE_LEVEL_TABLE = {
    "first": 1,
    "second": 2,
    "third": (3, 4, 5),
}


class Base(object):
    kind = "base"
    slots_used = False

    def __init__(self, name, value=0):
        self.name = name
        self.value = value
        self.children = []

    def __repr__(self):
        return "<%s %s=%r>" % (self.__class__.__name__, self.name, self.value)

    def __eq__(self, other):
        return self.name == other.name and self.value == other.value

    def __hash__(self):
        return hash((self.name, self.value))

    def add(self, child):
        self.children.append(child)
        return self

    @property
    def size(self):
        return len(self.children)

    @staticmethod
    def describe():
        return "a base class"

    @classmethod
    def make(cls, name):
        return cls(name)


class Derived(Base):
    kind = "derived"

    def __init__(self, name, value=0, extra=None):
        Base.__init__(self, name, value)

        self.extra = extra or {}

    def add(self, child):
        result = super(Derived, self).add(child)
        self.extra[child] = self.size

        return result

    @property
    def size(self):
        return super(Derived, self).size * 2


class SlottedNode(object):
    __slots__ = ("name", "parent", "flags")

    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent
        self.flags = 0

    def getPath(self):
        parts = []
        current = self

        while current is not None:
            parts.append(current.name)
            current = current.parent

        return join(*reversed(parts))


class Mixin(object):
    def combined(self):
        return "%s/%s" % (self.kind, self.name)


class Multiple(Mixin, Derived):
    kind = "multiple"

    def combined(self):
        return Mixin.combined(self).upper()


class WithNestedClass(object):
    class Inner(object):
        value = 1

        class Innermost(object):
            value = 2

    def get(self):
        return self.Inner.Innermost.value


class Container(object):
    def __init__(self, items=()):
        self.items = list(items)

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

    def __getitem__(self, index):
        return self.items[index]

    def __setitem__(self, index, value):
        self.items[index] = value

    def __contains__(self, value):
        return value in self.items

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        del self.items[:]
        return False


def build_registry(names):
    registry = OrderedDict()
    counts = defaultdict(int)

    for name in names:
        node = Derived(name, value=len(name))
        registry[name] = node
        counts[len(name)] += 1

    return registry, counts


def use_imports(filename):
    return (
        basename(filename),
        dirname(filename),
        os.path.abspath(filename),
        os.sep,
        sys.platform,
        collections.namedtuple("Pair", "first second"),
    )


def local_import(name):
    import json

    return json.dumps({"name": name})


def conditional_import():
    try:
        from cStringIO import StringIO
    except ImportError:
        from io import StringIO

    return StringIO


def make_type(name, bases, namespace):
    return type(name, bases, dict(namespace, created=True))


def instance_work(count):
    root = Multiple("root", value=count)

    for index in range(count):
        node = SlottedNode("node%d" % index, parent=None)
        root.add(node.name)

    with Container(range(count)) as container:
        total = sum(value for value in container if value in container)

    return root.combined(), total, MODULE_LEVEL_TABLE
