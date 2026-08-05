#     Copyright 2026, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file


"""Code generation for switch-like match dispatch."""

from .CodeHelpers import generateStatementSequenceCode
from .ConditionalCodes import generateConditionCode
from .Emission import withSubCollector
from .LabelCodes import getGotoCode, getLabelCode
from .VariableCodes import getLocalVariableDeclaration
from nuitka.PythonVersions import sizeof_clong


_min_signed_long = -(2 ** (sizeof_clong * 8 - 1))


def _getCaseValueCode(value):
    if value == _min_signed_long:
        return "LONG_MIN"

    return "%dL" % value


def generateSwitchCode(statement, emit, context):
    end_target = context.allocateLabel("switch_end")
    fallback_target = context.allocateLabel("switch_fallback")
    case_targets = [context.allocateLabel("switch_case") for _ in statement.case_values]

    subject = statement.subnode_subject
    subject_declaration = getLocalVariableDeclaration(
        context=context,
        variable=subject.getVariable(),
        variable_trace=subject.getVariableTrace(),
    )

    switch_value = context.allocateTempName("switch_value", type_name="long")
    overflow = context.allocateTempName("switch_overflow", type_name="int")

    emit("if (PyLong_CheckExact(%s)) {" % subject_declaration)
    emit(
        "%s = Nuitka_PyLong_AsLongAndOverflow(%s, &%s);"
        % (switch_value, subject_declaration, overflow)
    )
    emit("if (%s == 0) {" % overflow)
    emit("switch (%s) {" % switch_value)

    for values, case_target in zip(statement.case_values, case_targets):
        for value in values:
            emit("case %s:" % _getCaseValueCode(value))
        getGotoCode(case_target, emit)

    emit("default:")
    getGotoCode(end_target, emit)
    emit("}")
    emit("}")
    emit("goto %s;" % fallback_target)
    emit("}")

    getLabelCode(fallback_target, emit)

    for count, condition in enumerate(statement.subnode_conditions):
        true_target = case_targets[count]
        false_target = (
            context.allocateLabel("switch_next")
            if count + 1 < len(statement.subnode_conditions)
            else end_target
        )

        old_true_target = context.getTrueBranchTarget()
        old_false_target = context.getFalseBranchTarget()
        context.setTrueBranchTarget(true_target)
        context.setFalseBranchTarget(false_target)

        with withSubCollector(emit, context) as condition_emit:
            generateConditionCode(
                condition=condition, emit=condition_emit, context=context
            )

        context.setTrueBranchTarget(old_true_target)
        context.setFalseBranchTarget(old_false_target)

        if count + 1 < len(statement.subnode_conditions):
            getLabelCode(false_target, emit)

    getGotoCode(end_target, emit)

    for case_target, branch in zip(case_targets, statement.subnode_branches):
        getLabelCode(case_target, emit)
        emit("{")
        generateStatementSequenceCode(
            statement_sequence=branch, emit=emit, context=context
        )
        getGotoCode(end_target, emit)
        emit("}")

    getLabelCode(end_target, emit)
