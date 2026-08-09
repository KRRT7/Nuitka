#     Copyright 2026, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file


"""Node for the calls to the 'next' built-in and unpacking special next.

The unpacking next has only special that it raises a different exception
text, explaining things about its context.
"""

from .ChildrenHavingMixins import ChildrenHavingIteratorDefaultMixin
from .ExpressionBases import ExpressionBase, ExpressionBuiltinSingleArgBase
from .shapes.StandardShapes import tshape_unknown


class ExpressionBuiltinNext1(ExpressionBuiltinSingleArgBase):
    __slots__ = ("may_raise",)

    kind = "EXPRESSION_BUILTIN_NEXT1"

    def __init__(self, value, source_ref):
        ExpressionBuiltinSingleArgBase.__init__(
            self, value=value, source_ref=source_ref
        )

        self.may_raise = True

    def computeExpression(self, trace_collection):
        self.may_raise, result = self.subnode_value.computeExpressionNext1(
            next_node=self, trace_collection=trace_collection
        )

        return result

    def mayRaiseExceptionOperation(self):
        return self.may_raise

    def mayRaiseException(self, exception_type):
        return self.may_raise or self.subnode_value.mayRaiseException(exception_type)

    # Note: These must not be given as the elements of this value. What this
    # produces is one element of the iterated value, and the elements of that
    # element are not the elements of the iterator, so answering with those
    # describes an entirely different sequence, and picking operations from it
    # then generates code for the wrong type.

    def _getIteratedValue(self, element_index):
        """Value or shape of an element of the iterated value, or None."""

        if hasattr(self.subnode_value, "getIterationValue"):
            result = self.subnode_value.getIterationValue(element_index)

            if result is not None:
                return result.getTypeShape()

        if hasattr(self.subnode_value, "getIterationValueShape"):
            return self.subnode_value.getIterationValueShape(element_index)

        return None

    def getTypeShape(self):
        # What "next" gives is the first element of what is iterated.
        result = self._getIteratedValue(0)

        if result is None:
            return tshape_unknown

        return result


class ExpressionSpecialUnpack(ExpressionBuiltinNext1):
    __slots__ = ("count", "expected", "starred")

    kind = "EXPRESSION_SPECIAL_UNPACK"

    def __init__(self, value, count, expected, starred, source_ref):
        ExpressionBuiltinNext1.__init__(self, value=value, source_ref=source_ref)

        self.count = int(count)

        # TODO: Unused before 3.5 or higher, and even then starred is rare, maybe specialize for it.
        self.expected = int(expected)
        self.starred = starred

    def getDetails(self):
        result = ExpressionBuiltinNext1.getDetails(self)
        result["count"] = self.getCount()
        result["expected"] = self.getExpected()
        result["starred"] = self.getStarred()
        return result

    def getCount(self):
        return self.count

    def getExpected(self):
        return self.expected

    def getStarred(self):
        return self.starred

    def getTypeShape(self):
        # Unpacking takes the elements of the value being unpacked, which the
        # iterator over it is asked for, and it can only answer when that value
        # is known by itself.
        element_index = self.count - 1
        iteration_length = self.subnode_value.getIterationLength()

        if iteration_length is not None and element_index >= iteration_length:
            return tshape_unknown

        try:
            result = self._getIteratedValue(element_index)
        except (AssertionError, IndexError):
            result = None

        if result is None:
            return tshape_unknown

        return result


class ExpressionBuiltinNext2(ChildrenHavingIteratorDefaultMixin, ExpressionBase):
    kind = "EXPRESSION_BUILTIN_NEXT2"

    named_children = ("iterator", "default")

    def __init__(self, iterator, default, source_ref):
        ChildrenHavingIteratorDefaultMixin.__init__(
            self,
            iterator=iterator,
            default=default,
        )

        ExpressionBase.__init__(self, source_ref)

    def computeExpression(self, trace_collection):
        # TODO: The "iterator" should be investigated here, if it is iterable,
        # or if the default is raising.

        # Any code could be run, note that.
        trace_collection.onControlFlowEscape(self)

        # Any exception may be raised.
        trace_collection.onExceptionRaiseExit(BaseException)

        return self, None, None


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
