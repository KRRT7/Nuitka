#     Copyright 2026, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file


"""Nodes for the calls to the 'min' and 'max' built-ins.

Only the form with exactly two values is done here. The one with an iterable
has to loop, and the ones with "key" or "default" given change the semantics,
so those are left to the normal call.
"""

from .ChildrenHavingMixins import ChildrenHavingLeftRightMixin
from .ExpressionBases import ExpressionBase


class ExpressionBuiltinMinMax2Mixin(object):
    # Mixins are required to define empty slots
    __slots__ = ()

    def __init__(self, left, right, source_ref):
        ChildrenHavingLeftRightMixin.__init__(self, left=left, right=right)

        ExpressionBase.__init__(self, source_ref)

    def computeExpression(self, trace_collection):
        left = self.subnode_left
        right = self.subnode_right

        if left.isCompileTimeConstant() and right.isCompileTimeConstant():
            return trace_collection.getCompileTimeComputationResult(
                node=self,
                computation=lambda: self.simulator(
                    left.getCompileTimeConstant(), right.getCompileTimeConstant()
                ),
                description="Built-in call to '%s' computed." % self.builtin_name,
            )

        # The comparison of the two values can raise for mismatching types.
        trace_collection.onExceptionRaiseExit(BaseException)

        return self, None, None


class ExpressionBuiltinMin2(
    ExpressionBuiltinMinMax2Mixin, ChildrenHavingLeftRightMixin, ExpressionBase
):
    kind = "EXPRESSION_BUILTIN_MIN2"

    named_children = ("left", "right")

    builtin_name = "min"
    simulator = staticmethod(min)


class ExpressionBuiltinMax2(
    ExpressionBuiltinMinMax2Mixin, ChildrenHavingLeftRightMixin, ExpressionBase
):
    kind = "EXPRESSION_BUILTIN_MAX2"

    named_children = ("left", "right")

    builtin_name = "max"
    simulator = staticmethod(max)


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
