#     Copyright 2026, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file


"""State of the names bound in the module during parsing.

Variable closures are only completed once a module is fully built, so during
building there is no way to ask what a name will refer to. For the cases where
building wants to know that a name is still the built-in one, this collects
every name that the module binds anywhere, from the unparsed tree, ahead of
building it.

That is an over-approximation on purpose. A name bound in an unrelated function
also counts, which merely gives up an optimization, whereas missing a binding
would change behavior.
"""

import ast

_bound_names = []


def _collectBoundNames(ast_tree):
    result = set()

    for node in ast.walk(ast_tree):
        # Assignments, deletions, loop and "with" targets, comprehension
        # targets, and the walrus operator all become a name store.
        if node.__class__ is ast.Name:
            if node.ctx.__class__ is not ast.Load:
                result.add(node.id)
        elif node.__class__ is ast.arg:
            result.add(node.arg)
        elif node.__class__ in (
            ast.FunctionDef,
            ast.AsyncFunctionDef,
            ast.ClassDef,
        ):
            result.add(node.name)
        elif node.__class__ is ast.alias:
            # "import x.y" binds "x", "import x as y" binds "y".
            result.add(node.asname or node.name.split(".")[0])
        elif node.__class__ is ast.ExceptHandler:
            if node.name is not None:
                result.add(node.name)
        elif node.__class__ in (ast.Global, ast.Nonlocal):
            result.update(node.names)
        elif node.__class__.__name__ in (
            # Match statements from Python 3.10 on, capturing names without
            # using a "Name" node for them.
            "MatchAs",
            "MatchStar",
        ):
            if node.name is not None:
                result.add(node.name)
        elif node.__class__.__name__ == "MatchMapping":
            if node.rest is not None:
                result.add(node.rest)

    return result


def pushBoundNames(ast_tree):
    _bound_names.append(_collectBoundNames(ast_tree))


def isNameBoundInModule(name):
    """Is the name bound anywhere in the module being built.

    When it is not, a reference to it cannot be anything but the built-in of
    that name, short of the module dictionary being changed from the outside,
    which is what optimization assumes as well.
    """
    # Outside of building a module, e.g. for generated code, assume the worst.
    if not _bound_names:
        return True

    return name in _bound_names[-1]


def popBoundNames():
    del _bound_names[-1]


#     Part of "Nuitka", an optimizing Python compiler that is compatible and
#     integrates with CPython, but also works on its own.
#
#     Licensed under the GNU Affero General Public License, Version 3 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#        https://www.gnu.org/licenses/agpl-3.0.txt
#
#     See also: "Nuitka Runtime Library Exception, Version 1.0" in file
#     "LICENSE-RUNTIME.txt" for additional permissions granted under Section 7.
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
