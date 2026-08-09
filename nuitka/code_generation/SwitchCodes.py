#     Copyright 2026, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file


"""Code generation for switch-like match dispatch."""

from nuitka.PythonVersions import sizeof_clong

from .CodeHelpers import generateStatementSequenceCode
from .ConditionalCodes import generateConditionCode
from .Emission import withSubCollector
from .LabelCodes import getGotoCode, getLabelCode
from .VariableCodes import getLocalVariableDeclaration

_min_signed_long = -(2 ** (sizeof_clong * 8 - 1))


def _getCaseValueCode(value):
    if value == _min_signed_long:
        return "LONG_MIN"

    return "%dL" % value


def _isSparseCaseValues(case_values):
    values = [value for values in case_values for value in values]

    if len(values) < 2:
        return False

    return max(values) - min(values) > len(values) * 8


def _isStringCaseValues(case_values):
    return all(type(value) is str for values in case_values for value in values)


def generateSwitchCode(statement, emit, context):
    end_target = context.allocateLabel("switch_end")
    default_target = context.allocateLabel("switch_default")
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

    if _isStringCaseValues(statement.case_values):
        string_hash = context.allocateTempName("switch_hash", type_name="Py_hash_t")
        emit("if (PyUnicode_CheckExact(%s)) {" % subject_declaration)
        emit("%s = PyObject_Hash(%s);" % (string_hash, subject_declaration))
        emit("if (%s != -1) {" % string_hash)
        for values, case_target in zip(statement.case_values, case_targets):
            checks = []
            for value in values:
                constant_code = context.getConstantCode(constant=value)
                checks.append(
                    "(PyUnicode_GET_LENGTH(%s) == %d && %s == PyObject_Hash(%s) && PyObject_RichCompareBool(%s, %s, Py_EQ) == 1)"
                    % (
                        subject_declaration,
                        len(value),
                        string_hash,
                        constant_code,
                        subject_declaration,
                        constant_code,
                    )
                )
            emit("if (%s) {" % " || ".join(checks))
            getGotoCode(case_target, emit)
            emit("}")
        emit("}")
    else:
        emit("if (PyLong_CheckExact(%s)) {" % subject_declaration)
        emit(
            "%s = Nuitka_PyLong_AsLongAndOverflow(%s, &%s);"
            % (switch_value, subject_declaration, overflow)
        )
        emit("if (%s == 0) {" % overflow)
    if (
        not _isStringCaseValues(statement.case_values)
        and len(statement.case_values) == 1
    ):
        values = statement.case_values[0]
        condition = " || ".join(
            "%s == %s" % (switch_value, _getCaseValueCode(value)) for value in values
        )
        emit("if (%s) {" % condition)
        getGotoCode(case_targets[0], emit)
        emit("}")
        getGotoCode(end_target, emit)
    elif not _isStringCaseValues(statement.case_values) and _isSparseCaseValues(
        statement.case_values
    ):
        for values, case_target in zip(statement.case_values, case_targets):
            condition = " || ".join(
                "%s == %s" % (switch_value, _getCaseValueCode(value))
                for value in values
            )
            emit("if (%s) {" % condition)
            getGotoCode(case_target, emit)
            emit("}")

        getGotoCode(default_target, emit)
    elif not _isStringCaseValues(statement.case_values):
        emit("switch (%s) {" % switch_value)

        for values, case_target in zip(statement.case_values, case_targets):
            for value in values:
                emit("case %s:" % _getCaseValueCode(value))
            getGotoCode(case_target, emit)

        emit("default:")
        getGotoCode(default_target, emit)
        emit("}")
    if not _isStringCaseValues(statement.case_values):
        emit("}")
    emit("goto %s;" % fallback_target)
    emit("}")

    getLabelCode(fallback_target, emit)

    for count, condition in enumerate(statement.subnode_conditions):
        true_target = case_targets[count]
        false_target = (
            context.allocateLabel("switch_next")
            if count + 1 < len(statement.subnode_conditions)
            else default_target
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

    getGotoCode(default_target, emit)

    for case_target, branch in zip(case_targets, statement.subnode_branches):
        getLabelCode(case_target, emit)
        emit("{")
        generateStatementSequenceCode(
            statement_sequence=branch, emit=emit, context=context
        )
        getGotoCode(end_target, emit)
        emit("}")

    getLabelCode(default_target, emit)
    if statement.subnode_default_branch is not None:
        emit("{")
        generateStatementSequenceCode(
            statement_sequence=statement.subnode_default_branch,
            emit=emit,
            context=context,
        )
        emit("}")

    getLabelCode(end_target, emit)
