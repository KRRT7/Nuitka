#     Copyright 2026, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file


"""Branch related codes."""

from nuitka.__past__ import long

from .CodeHelpers import generateStatementSequenceCode
from .ConditionalCodes import generateConditionCode
from .Emission import withSubCollector
from .LabelCodes import getGotoCode, getLabelCode


def _isSwitchCaseConstant(constant):
    return type(constant) in (int, long) and -2147483647 <= constant <= 2147483647


def _getSwitchConditionInfo(condition):
    if not condition.isExpressionComparison() or condition.getComparator() != "Eq":
        return None

    left, right = condition.getOperands()

    if left.isExpressionVariableRefOrTempVariableRef():
        variable_ref = left
        constant_ref = right
    elif right.isExpressionVariableRefOrTempVariableRef():
        variable_ref = right
        constant_ref = left
    else:
        return None

    if not constant_ref.isCompileTimeConstant():
        return None

    constant = constant_ref.getCompileTimeConstant()

    if not _isSwitchCaseConstant(constant):
        return None

    return variable_ref, constant


def _getSwitchChain(statement):
    cases = []
    switch_variable = None
    switch_variable_trace = None
    current = statement

    while current.isStatementConditional():
        switch_info = _getSwitchConditionInfo(current.subnode_condition)

        if switch_info is None:
            return None

        variable_ref, constant = switch_info
        variable = variable_ref.getVariable()

        if switch_variable is None:
            switch_variable = variable
            switch_variable_trace = variable_ref.getVariableTrace()
        elif switch_variable is not variable:
            return None

        cases.append((constant, current.subnode_yes_branch, current.subnode_condition))

        no_branch = current.subnode_no_branch

        if (
            no_branch is not None
            and len(no_branch.subnode_statements) == 1
            and no_branch.subnode_statements[0].isStatementConditional()
        ):
            current = no_branch.subnode_statements[0]
        else:
            constants = [constant for constant, _yes_branch, _condition in cases]

            if len(cases) < 3 or len(constants) != len(set(constants)):
                return None

            return switch_variable, switch_variable_trace, cases, no_branch

    return None


def _getSwitchValueName(switch_variable, switch_variable_trace, context):
    # Avoid import cycle.
    from .VariableCodes import getLocalVariableDeclaration

    if not switch_variable.isLocalVariable():
        return None

    variable_declaration = getLocalVariableDeclaration(
        context=context, variable=switch_variable, variable_trace=switch_variable_trace
    )

    if variable_declaration.c_type != "PyObject *":
        return None

    return variable_declaration


def _generateSwitchDispatchCode(statement, emit, context):
    switch_chain = _getSwitchChain(statement)

    if switch_chain is None:
        return False

    switch_variable, switch_variable_trace, cases, default_branch = switch_chain
    switch_value_name = _getSwitchValueName(
        switch_variable=switch_variable,
        switch_variable_trace=switch_variable_trace,
        context=context,
    )

    if switch_value_name is None:
        return False

    case_labels = [context.allocateLabel("switch_case") for _case in cases]
    default_label = context.allocateLabel("switch_default")
    end_label = context.allocateLabel("switch_end")

    switch_value_long = context.allocateTempName("switch_value", "long")
    switch_overflow = context.allocateTempName("switch_overflow", "int")

    emit(
        "if (%s != NULL && PyLong_CheckExact(%s)) {"
        % (switch_value_name, switch_value_name)
    )
    emit("%s = 0;" % switch_overflow)
    emit(
        "%s = Nuitka_PyLong_AsLongAndOverflow(%s, &%s);"
        % (switch_value_long, switch_value_name, switch_overflow)
    )
    emit("if (%s == 0) {" % switch_overflow)
    emit("switch (%s) {" % switch_value_long)

    for case_label, (constant, _yes_branch, _condition) in zip(case_labels, cases):
        emit("case %d:" % constant)
        getGotoCode(case_label, emit)

    emit("default:")
    getGotoCode(default_label, emit)
    emit("}")
    emit("}")
    emit("}")

    old_true_target = context.getTrueBranchTarget()
    old_false_target = context.getFalseBranchTarget()

    for case_label, (_constant, _yes_branch, condition) in zip(case_labels, cases):
        next_label = context.allocateLabel("switch_next")

        context.setTrueBranchTarget(case_label)
        context.setFalseBranchTarget(next_label)

        with withSubCollector(emit, context) as condition_emit:
            generateConditionCode(
                condition=condition, emit=condition_emit, context=context
            )

        getLabelCode(next_label, emit)

    context.setTrueBranchTarget(old_true_target)
    context.setFalseBranchTarget(old_false_target)

    getGotoCode(default_label, emit)

    for case_label, (_constant, yes_branch, _condition) in zip(case_labels, cases):
        getLabelCode(case_label, emit)

        generateStatementSequenceCode(
            statement_sequence=yes_branch, emit=emit, context=context
        )

        getGotoCode(end_label, emit)

    getLabelCode(default_label, emit)

    if default_branch is not None:
        generateStatementSequenceCode(
            statement_sequence=default_branch, emit=emit, context=context
        )

    getLabelCode(end_label, emit)

    return True


def generateBranchCode(statement, emit, context):
    if _generateSwitchDispatchCode(statement=statement, emit=emit, context=context):
        return

    true_target = context.allocateLabel("branch_yes")
    false_target = context.allocateLabel("branch_no")
    end_target = context.allocateLabel("branch_end")

    old_true_target = context.getTrueBranchTarget()
    old_false_target = context.getFalseBranchTarget()

    context.setTrueBranchTarget(true_target)
    context.setFalseBranchTarget(false_target)

    # Have own declaration scope for condition, to limit visibility from branches
    # which can be huge.
    with withSubCollector(emit, context) as condition_emit:
        generateConditionCode(
            condition=statement.subnode_condition, emit=condition_emit, context=context
        )

    context.setTrueBranchTarget(old_true_target)
    context.setFalseBranchTarget(old_false_target)

    getLabelCode(true_target, emit)

    generateStatementSequenceCode(
        statement_sequence=statement.subnode_yes_branch, emit=emit, context=context
    )

    if statement.subnode_no_branch is not None:
        getGotoCode(end_target, emit)
        getLabelCode(false_target, emit)

        generateStatementSequenceCode(
            statement_sequence=statement.subnode_no_branch, emit=emit, context=context
        )

        getLabelCode(end_target, emit)
    else:
        getLabelCode(false_target, emit)


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
