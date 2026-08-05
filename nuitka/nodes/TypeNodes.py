#     Copyright 2026, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file


"""The type nodes.

These ones deal with types and they are great for optimization. We need to know
them, their relationship or check for them in re-formulations.

"""

from nuitka.__past__ import GenericAlias
from nuitka.Builtins import builtin_names
from nuitka.options.Options import isExperimental

from .BuiltinRefNodes import (
    ExpressionBuiltinAnonymousRef,
    ExpressionBuiltinRef,
    makeExpressionBuiltinRef,
)
from .ChildrenHavingMixins import (
    ChildHavingClsMixin,
    ChildrenExpressionBuiltinIssubclassMixin,
    ChildrenExpressionBuiltinSuper0Mixin,
    ChildrenExpressionBuiltinSuper1Mixin,
    ChildrenExpressionBuiltinSuper2Mixin,
    ChildrenExpressionTypeAliasMixin,
    ChildrenExpressionTypeMakeGenericMixin,
    ChildrenHavingInstanceClassesMixin,
    ChildrenHavingLeftRightMixin,
)
from .ExpressionBases import ExpressionBase, ExpressionBuiltinSingleArgBase
from .ExpressionBasesGenerated import (
    ExpressionParameterSpecificationBase,
    ExpressionSubtypeCheckBase,
    ExpressionTypeVariableBase,
    ExpressionTypeVariableTupleBase,
)
from .ExpressionShapeMixins import ExpressionBoolShapeExactMixin
from .NodeBases import SideEffectsFromChildrenMixin
from .NodeMakingHelpers import (
    makeConstantReplacementNode,
    wrapExpressionWithNodeSideEffects,
)
from .ConstantRefNodes import makeConstantRefNode
from .shapes.BuiltinTypeShapes import tshape_bool, tshape_type


# Mapping from Python type objects to C API type pointer names.
# Used by ExpressionTypeIdentityCheck to generate direct Py_TYPE() comparisons.
TYPE_TO_C_NAME = {
    bool: "PyBool_Type",
    int: "PyLong_Type",
    float: "PyFloat_Type",
    complex: "PyComplex_Type",
    str: "PyUnicode_Type",
    bytes: "PyBytes_Type",
    bytearray: "PyByteArray_Type",
    memoryview: "PyMemoryView_Type",
    tuple: "PyTuple_Type",
    list: "PyList_Type",
    dict: "PyDict_Type",
    set: "PySet_Type",
    frozenset: "PyFrozenSet_Type",
    type: "PyType_Type",
    type(None): "PyNone_Type",
    type(Ellipsis): "PyEllipsis_Type",
    type(NotImplemented): "PyNotImplemented_Type",
}


def getTypeConstantCName(type_constant):
    """Return the C type pointer name for a given type constant node, or None.

    The node must be a compile-time constant representing a type object
    (e.g. ExpressionConstantTypeTupleRef for 'tuple'). Returns the C-level
    name like 'PyTuple_Type' if the type is a known builtin, otherwise None.
    """
    type_obj = None

    if type_constant.isExpressionConstantTypeRef():
        type_obj = type_constant.getCompileTimeConstant()
    elif type_constant.isExpressionBuiltinRef():
        builtin_name = type_constant.builtin_name
        try:
            type_obj = __builtins__[builtin_name]
        except KeyError:
            return None
        if not isinstance(type_obj, type):
            return None
    elif type_constant.isExpressionBuiltinAnonymousRef():
        try:
            type_obj = type_constant.getCompileTimeConstant()
        except KeyError:
            return None

    return TYPE_TO_C_NAME.get(type_obj) if type_obj is not None else None


# Types whose C pointer variables are private in CPython 3.13+ and must
# be accessed at runtime via Py_TYPE() of the corresponding singleton.
_PRIVATE_TYPE_C_NAMES = {
    "PyNone_Type": "Py_TYPE(Py_None)",
    "PyNotImplemented_Type": "Py_TYPE(Py_NotImplemented)",
}


def getTypeConstantCExpression(c_name):
    """Return a C expression that evaluates to a pointer to the type object.

    For public types like PyLong_Type, this returns '&PyLong_Type'.
    For private types in CPython 3.13+ (PyNone_Type, PyNotImplemented_Type),
    this returns the runtime expression 'Py_TYPE(Py_None)' etc.
    """
    if c_name in _PRIVATE_TYPE_C_NAMES:
        return _PRIVATE_TYPE_C_NAMES[c_name]
    return "&%s" % c_name


def isTypeConstantNode(node):
    """Check whether a node represents a compile-time constant type.

    This covers ExpressionConstantTypeRef, ExpressionBuiltinRef (for type
    names like int/float/str), and ExpressionBuiltinAnonymousRef (for
    NoneType, ellipsis, etc.).
    """
    if node.isExpressionConstantTypeRef():
        return True
    if node.isExpressionBuiltinRef():
        builtin_name = node.builtin_name
        try:
            obj = __builtins__[builtin_name]
        except KeyError:
            return False
        return isinstance(obj, type)
    if node.isExpressionBuiltinAnonymousRef():
        try:
            obj = node.getCompileTimeConstant()
        except KeyError:
            return False
        return isinstance(obj, type)
    return False


def tryExtractTypeCNames(classes_node):
    """Extract C type names from a compile-time type constant.

    Handles both single types (e.g. ``isinstance(x, int)``) and tuples of
    types (e.g. ``isinstance(x, (int, float))``). Returns a tuple of C type
    pointer names (like ``('PyLong_Type', 'PyFloat_Type')``) if all types
    are known builtins, otherwise returns None.
    """
    c_names = []

    if classes_node.isExpressionConstantTypeRef():
        c_name = getTypeConstantCName(classes_node)
        if c_name is None:
            return None
        c_names.append(c_name)
    elif classes_node.isExpressionConstantTupleRef():
        # isinstance(x, (int, float, str, ...)) — tuple of types.
        const_value = classes_node.getCompileTimeConstant()
        for element in const_value:
            elem_node = makeConstantRefNode(
                constant=element, source_ref=classes_node.source_ref
            )
            c_name = getTypeConstantCName(elem_node)
            if c_name is None:
                return None
            c_names.append(c_name)
    elif classes_node.isExpressionBuiltinRef():
        c_name = getTypeConstantCName(classes_node)
        if c_name is None:
            return None
        c_names.append(c_name)
    elif classes_node.isExpressionBuiltinAnonymousRef():
        c_name = getTypeConstantCName(classes_node)
        if c_name is None:
            return None
        c_names.append(c_name)
    else:
        return None

    return tuple(c_names)


class ExpressionBuiltinType1(ExpressionBuiltinSingleArgBase):
    kind = "EXPRESSION_BUILTIN_TYPE1"

    def computeExpression(self, trace_collection):
        value = self.subnode_value

        type_shape = value.getTypeShape()

        if type_shape is not None:
            type_name = type_shape.getTypeName()

            if type_name is not None:
                if isExperimental("assume-type-complete") and hasattr(
                    type_shape, "typical_value"
                ):
                    result = makeConstantReplacementNode(
                        constant=type(getattr(type_shape, "typical_value")),
                        node=self,
                        user_provided=False,
                    )
                elif type_name in __builtins__:
                    result = ExpressionBuiltinRef(
                        builtin_name=type_name, source_ref=value.getSourceReference()
                    )
                else:
                    result = None

                # TODO: Does this even happen to be not None
                if result is not None:
                    result = wrapExpressionWithNodeSideEffects(
                        new_node=result, old_node=value
                    )

                    return (
                        result,
                        "new_builtin",
                        "Replaced predictable type lookup with builtin type '%s'."
                        % (type_name),
                    )

        if value.isCompileTimeConstant():
            # The above code is supposed to catch these in a better way.
            value = value.getCompileTimeConstant()

            if type(value) is GenericAlias:
                type_name = "GenericAlias"
            else:
                type_name = value.__class__.__name__

            if type_name in builtin_names:
                new_node = makeExpressionBuiltinRef(
                    builtin_name=type_name,
                    locals_scope=None,
                    source_ref=self.source_ref,
                )
            else:
                new_node = ExpressionBuiltinAnonymousRef(
                    builtin_name=type_name, source_ref=self.source_ref
                )

            return (
                new_node,
                "new_builtin",
                "Replaced predictable type lookup with builtin type '%s'."
                % (type_name),
            )

        return self, None, None

    @staticmethod
    def getTypeShape():
        return tshape_type

    def computeExpressionDrop(self, statement, trace_collection):
        from .NodeMakingHelpers import (
            makeStatementExpressionOnlyReplacementNode,
        )

        result = makeStatementExpressionOnlyReplacementNode(
            expression=self.subnode_value, node=statement
        )

        return (
            result,
            "new_statements",
            """\
Removed type taking for unused result.""",
        )

    def mayRaiseException(self, exception_type):
        return self.subnode_value.mayRaiseException(exception_type)

    def mayHaveSideEffects(self):
        return self.subnode_value.mayHaveSideEffects()


class ExpressionTypeIdentityCheck(
    ExpressionBoolShapeExactMixin,
    SideEffectsFromChildrenMixin,
    ChildrenHavingLeftRightMixin,
    ExpressionBase,
):
    """Check if type(x) is T or type(x) is not T.

    This replaces an ExpressionComparisonIs[Not] whose left is
    ExpressionBuiltinType1(value) and whose right is a type constant.
    It generates Py_TYPE(value) == (PyTypeObject *)&PyT_Type instead of
    BUILTIN_TYPE1 + PyObject_RichCompare + Py_DECREF.

    'left' child is the value expression (the argument to type()).
    'right' child is the type constant expression being compared against.
    """

    kind = "EXPRESSION_TYPE_IDENTITY_CHECK"

    named_children = ("left", "right")

    __slots__ = ("negated",)

    def __init__(self, left, right, negated, source_ref):
        ChildrenHavingLeftRightMixin.__init__(self, left=left, right=right)

        ExpressionBase.__init__(self, source_ref)

        self.negated = negated

    def computeExpression(self, trace_collection):
        # Try to fold if both the value and the type constant are
        # compile-time constants.
        value = self.subnode_left
        type_constant = self.subnode_right

        if value.isCompileTimeConstant() and type_constant.isCompileTimeConstant():
            value_const = value.getCompileTimeConstant()
            type_const = type_constant.getCompileTimeConstant()

            result = type(value_const) is type_const
            if self.negated:
                result = not result

            new_node = makeConstantRefNode(
                constant=result, source_ref=self.source_ref
            )

            return (
                new_node,
                "new_builtin",
                "Replaced type identity check with compile time constant.",
            )

        return self, None, None

    @staticmethod
    def getTypeShape():
        return tshape_bool

    def mayRaiseException(self, exception_type):
        return self.subnode_left.mayRaiseException(exception_type)

    def mayHaveSideEffects(self):
        return self.subnode_left.mayHaveSideEffects()

    def mayReturnValue(self):
        return True

    def mayReturnUserspaceValue(self):
        return True


class ExpressionBuiltinSuper1(ChildrenExpressionBuiltinSuper1Mixin, ExpressionBase):
    """Two arguments form of super."""

    kind = "EXPRESSION_BUILTIN_SUPER1"

    named_children = ("type_arg",)

    def __init__(self, type_arg, source_ref):
        ChildrenExpressionBuiltinSuper1Mixin.__init__(
            self,
            type_arg=type_arg,
        )

        ExpressionBase.__init__(self, source_ref)

    def computeExpression(self, trace_collection):
        trace_collection.onExceptionRaiseExit(BaseException)

        # TODO: Quite some cases should be possible to predict.
        return self, None, None


class ExpressionBuiltinSuper2(ChildrenExpressionBuiltinSuper2Mixin, ExpressionBase):
    """Two arguments form of super."""

    kind = "EXPRESSION_BUILTIN_SUPER2"

    named_children = ("type_arg", "object_arg")

    def __init__(self, type_arg, object_arg, source_ref):
        ChildrenExpressionBuiltinSuper2Mixin.__init__(
            self,
            type_arg=type_arg,
            object_arg=object_arg,
        )

        ExpressionBase.__init__(self, source_ref)

    def computeExpression(self, trace_collection):
        trace_collection.onExceptionRaiseExit(BaseException)

        # TODO: Quite some cases should be possible to predict.
        return self, None, None


class ExpressionBuiltinSuper0(ChildrenExpressionBuiltinSuper0Mixin, ExpressionBase):
    """Python3 form of super, arguments determined from cells and function arguments."""

    kind = "EXPRESSION_BUILTIN_SUPER0"

    named_children = ("type_arg", "object_arg")

    def __init__(self, type_arg, object_arg, source_ref):
        ChildrenExpressionBuiltinSuper0Mixin.__init__(
            self,
            type_arg=type_arg,
            object_arg=object_arg,
        )

        ExpressionBase.__init__(self, source_ref)

    def computeExpression(self, trace_collection):
        trace_collection.onExceptionRaiseExit(BaseException)

        # TODO: Quite some cases should be possible to predict.
        return self, None, None


class ExpressionBuiltinIsinstance(ChildrenHavingInstanceClassesMixin, ExpressionBase):
    kind = "EXPRESSION_BUILTIN_ISINSTANCE"

    named_children = ("instance", "classes")

    __slots__ = ("type_c_names",)

    def __init__(self, instance, classes, source_ref):
        ChildrenHavingInstanceClassesMixin.__init__(
            self,
            instance=instance,
            classes=classes,
        )

        ExpressionBase.__init__(self, source_ref)

        self.type_c_names = None

    def computeExpression(self, trace_collection):
        # TODO: Quite some cases should be possible to predict.

        instance = self.subnode_instance

        classes = self.subnode_classes

        # Try to optimize with direct type checks when classes is a
        # compile-time constant of known builtin types.  We set the
        # type_c_names attribute on this node (rather than replacing the
        # node) so that the code generator can emit direct type checks.
        if classes.isCompileTimeConstant():
            type_c_names = tryExtractTypeCNames(classes)
            if type_c_names is not None:
                self.type_c_names = type_c_names

                if not instance.isCompileTimeConstant():
                    trace_collection.onExceptionRaiseExit(BaseException)

                # Return (self, None, None) — we are not replacing the node,
                # just annotating it for the code generator.  Using a change
                # tag would cause an infinite optimization loop.
                return self, None, None

        if not instance.isCompileTimeConstant():
            trace_collection.onExceptionRaiseExit(BaseException)

            return self, None, None

        if not classes.isCompileTimeConstant():
            trace_collection.onExceptionRaiseExit(BaseException)

            return self, None, None

        # So if both are compile time constant, we are able to compute it.
        return trace_collection.getCompileTimeComputationResult(
            node=self,
            computation=lambda: isinstance(
                instance.getCompileTimeConstant(), classes.getCompileTimeConstant()
            ),
            description="Built-in call to 'isinstance' computed.",
        )


class ExpressionBuiltinIssubclass(
    ChildrenExpressionBuiltinIssubclassMixin, ExpressionBase
):
    kind = "EXPRESSION_BUILTIN_ISSUBCLASS"

    named_children = ("cls", "classes")

    def __init__(self, cls, classes, source_ref):
        ChildrenExpressionBuiltinIssubclassMixin.__init__(
            self,
            cls=cls,
            classes=classes,
        )

        ExpressionBase.__init__(self, source_ref)

    def computeExpression(self, trace_collection):
        # TODO: Quite some cases should be possible to predict.

        cls = self.subnode_cls

        # TODO: Should be possible to query run time type instead, but we don't
        # have that method yet. Later this will be essential.
        if not cls.isCompileTimeConstant():
            trace_collection.onExceptionRaiseExit(BaseException)

            return self, None, None

        classes = self.subnode_classes

        if not classes.isCompileTimeConstant():
            trace_collection.onExceptionRaiseExit(BaseException)

            return self, None, None

        # So if both are compile time constant, we are able to compute it.
        return trace_collection.getCompileTimeComputationResult(
            node=self,
            computation=lambda: issubclass(
                cls.getCompileTimeConstant(), classes.getCompileTimeConstant()
            ),
            description="Built-in call to 'issubclass' computed.",
        )


class ExpressionTypeCheck(
    ExpressionBoolShapeExactMixin,
    SideEffectsFromChildrenMixin,
    ChildHavingClsMixin,
    ExpressionBase,
):
    kind = "EXPRESSION_TYPE_CHECK"

    named_children = ("cls",)

    def __init__(self, cls, source_ref):
        ChildHavingClsMixin.__init__(self, cls=cls)

        ExpressionBase.__init__(self, source_ref)

    def computeExpression(self, trace_collection):
        # TODO: Quite some cases should be possible to predict, but I am not aware of
        # 100% true Python equivalent at this time.
        return self, None, None


class ExpressionSubtypeCheck(
    ExpressionBoolShapeExactMixin,
    SideEffectsFromChildrenMixin,
    ExpressionSubtypeCheckBase,
):
    kind = "EXPRESSION_SUBTYPE_CHECK"

    named_children = ("left", "right")

    auto_compute_handling = "final,no_raise"

    def computeExpression(self, trace_collection):
        # TODO: This needs to check the MRO and can assume the type nature, since it's only coming
        # from re-formulations that guarantee that.
        return self, None, None


class ExpressionTypeAlias(ChildrenExpressionTypeAliasMixin, ExpressionBase):
    kind = "EXPRESSION_TYPE_ALIAS"

    named_children = ("name", "type_params|tuple", "value")

    def __init__(self, name, type_params, value, source_ref):
        ChildrenExpressionTypeAliasMixin.__init__(
            self, name=name, type_params=type_params, value=value
        )

        ExpressionBase.__init__(self, source_ref)

    def computeExpression(self, trace_collection):
        return self, None, None

    @staticmethod
    def mayRaiseExceptionOperation():
        return False


class ExpressionTypeVariable(ExpressionTypeVariableBase, ExpressionBase):
    kind = "EXPRESSION_TYPE_VARIABLE"

    auto_compute_handling = "final,no_raise"
    node_attributes = ("name",)

    python_version_spec = ">= 0x3c0"


class ExpressionTypeVariableTuple(ExpressionTypeVariableTupleBase, ExpressionBase):
    kind = "EXPRESSION_TYPE_VARIABLE_TUPLE"

    auto_compute_handling = "final,no_raise"
    node_attributes = ("name",)

    python_version_spec = ">= 0x3c0"


class ExpressionParameterSpecification(
    ExpressionParameterSpecificationBase, ExpressionBase
):
    kind = "EXPRESSION_PARAMETER_SPECIFICATION"

    auto_compute_handling = "final,no_raise"
    node_attributes = ("name",)

    python_version_spec = ">= 0x3c0"


class ExpressionTypeMakeGeneric(ChildrenExpressionTypeMakeGenericMixin, ExpressionBase):
    kind = "EXPRESSION_TYPE_MAKE_GENERIC"

    named_children = ("type_params",)

    def __init__(self, type_params, source_ref):
        ChildrenExpressionTypeMakeGenericMixin.__init__(self, type_params=type_params)

        ExpressionBase.__init__(self, source_ref)

    def computeExpression(self, trace_collection):
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
