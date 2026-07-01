#     Copyright 2026, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file


"""Emission of source code.

Code generation is driven via "emit", which is to receive lines of code and
this is to collect them, providing the emit implementation. Sometimes nested
use of these will occur.

"""


class SourceCodeCollector(list):
    __slots__ = ()

    __call__ = list.append
    emit = list.append


class _SubCollector:
    __slots__ = ("context", "emit", "sub_emit")

    def __init__(self, emit, context):
        self.emit = emit
        self.context = context

    def __enter__(self):
        context = self.context

        context.pushCleanupScope()
        context.variable_storage.variable_declarations_locals.append([])

        sub_emit = SourceCodeCollector()
        self.sub_emit = sub_emit

        # To use the collector and put code in it and C declarations on the context.
        return sub_emit

    def __exit__(self, exc_type, exc_value, traceback):
        context = self.context

        if exc_type is not None:
            context.variable_storage.variable_declarations_locals.pop()
            context.popCleanupScope()

            return False

        local_variable_declarations = (
            context.variable_storage.variable_declarations_locals.pop()
        )

        emit = self.emit

        if local_variable_declarations:
            emit("{")

            emit.extend(
                variable_declaration.makeCFunctionLevelDeclaration()
                for variable_declaration in local_variable_declarations
            )
            emit.extend(self.sub_emit)

            emit("}")
        else:
            emit.extend(self.sub_emit)

        context.popCleanupScope()

        return False


withSubCollector = _SubCollector


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
