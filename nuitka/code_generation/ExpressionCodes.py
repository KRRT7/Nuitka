#     Copyright 2026, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file


"""Expression codes, side effects, or statements that are an unused expression.

When you write "f()", i.e. you don't use the return value, that is an expression
only statement.

"""

from .CallCodes import getCallCodeNoArgs, getCallCodePosArgsQuick
from .CodeHelpers import generateExpressionCode
from .ErrorCodes import getErrorExitBoolCode, getReleaseCode
from .VariableCodes import getLocalVariableDeclaration


def generateExpressionOnlyCode(statement, emit, context):
    value = statement.subnode_expression

    if _generateTailSelfCallCode(value=value, emit=emit, context=context):
        return

    return getStatementOnlyCode(value=value, emit=emit, context=context)


def _getTailSelfCallDetails(value, context):
    if (
        not hasattr(context, "isForCreatedFunction")
        or not context.isForCreatedFunction()
    ):
        return None

    if not value.isExpressionCall() or value.subnode_kwargs is not None:
        return None

    called = value.subnode_called

    if not called.isExpressionVariableRefOrTempVariableRef():
        return None

    owner = context.getOwner()

    if called.getVariableName() != owner.getFunctionName():
        return None

    parameters = owner.getParameters()

    if (
        parameters.kw_only_variables
        or parameters.list_star_variable is not None
        or parameters.dict_star_variable is not None
    ):
        return None

    parameter_variables = parameters.pos_only_variables + parameters.normal_variables
    call_args = value.subnode_args

    if call_args is None:
        arg_expressions = ()
    elif call_args.isExpressionConstantTupleEmptyRef():
        arg_expressions = ()
    elif call_args.isExpressionMakeTuple():
        arg_expressions = call_args.subnode_elements
    else:
        return None

    if len(arg_expressions) != len(parameter_variables):
        return None

    parameter_declarations = []

    for variable in parameter_variables:
        variable_declaration = getLocalVariableDeclaration(
            context=context, variable=variable, variable_trace=None
        )

        if variable_declaration.c_type != "PyObject *":
            return None

        parameter_declarations.append(variable_declaration)

    return called, arg_expressions, parameter_declarations


def _generateTailSelfCallCode(value, emit, context):
    details = _getTailSelfCallDetails(value=value, context=context)

    if details is None:
        return False

    called, arg_expressions, parameter_declarations = details

    called_name = context.allocateTempName("tail_called")
    generateExpressionCode(
        to_name=called_name, expression=called, emit=emit, context=context
    )

    arg_names = []

    for arg_expression in arg_expressions:
        arg_name = context.allocateTempName("tail_arg")
        generateExpressionCode(
            to_name=arg_name, expression=arg_expression, emit=emit, context=context
        )

        arg_names.append(arg_name)

    emit("if (%s == (PyObject *)self) {" % called_name)

    getErrorExitBoolCode(
        condition="Nuitka_EnterTailRecursivePythonCall(tstate)",
        emit=emit,
        context=context,
    )

    emit("    nuitka_tail_recursion_depth += 1;")

    if context.needsCleanup(called_name):
        emit("    Py_DECREF(%s);" % called_name)

    for parameter_declaration in parameter_declarations:
        emit("    CHECK_OBJECT(%s);" % parameter_declaration)
        emit("    Py_DECREF(%s);" % parameter_declaration)

    for parameter_declaration, arg_name in zip(parameter_declarations, arg_names):
        if not context.needsCleanup(arg_name):
            emit("    Py_INCREF(%s);" % arg_name)

        emit("    %s = %s;" % (parameter_declaration, arg_name))

    emit("    goto function_tail_reentry;")
    emit("}")

    tmp_name = context.allocateTempName(base_name="unused_tail_call", unique=True)

    if arg_names:
        getCallCodePosArgsQuick(
            to_name=tmp_name,
            called_name=called_name,
            arg_names=arg_names,
            expression=value,
            emit=emit,
            context=context,
        )
    else:
        getCallCodeNoArgs(
            to_name=tmp_name,
            called_name=called_name,
            expression=value,
            emit=emit,
            context=context,
        )

    getReleaseCode(release_name=tmp_name, emit=emit, context=context)

    return True


def getStatementOnlyCode(value, emit, context):
    tmp_name = context.allocateTempName(
        base_name="unused", type_name="nuitka_void", unique=True
    )
    tmp_name.maybe_unused = True

    generateExpressionCode(
        expression=value, to_name=tmp_name, emit=emit, context=context
    )

    # An error of the expression is dealt inside of this, not necessary here,
    # but we have to release non-error value if it has a reference.
    getReleaseCode(release_name=tmp_name, emit=emit, context=context)


def generateSideEffectsCode(to_name, expression, emit, context):
    for side_effect in expression.subnode_side_effects:
        getStatementOnlyCode(value=side_effect, emit=emit, context=context)

    generateExpressionCode(
        to_name=to_name,
        expression=expression.subnode_expression,
        emit=emit,
        context=context,
    )


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
