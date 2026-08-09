#     Copyright 2026, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file


"""Attribute related codes.

Attribute lookup, setting.
"""

from nuitka.PythonVersions import python_version
from nuitka.States import states
from nuitka.utils.CStrings import encodePythonIdentifierToC
from nuitka.utils.Jinja2 import getTemplateC

from .CodeHelpers import (
    decideConversionCheckNeeded,
    generateChildExpressionsCode,
    generateExpressionCode,
    withObjectCodeTemporaryAssignment,
)
from .ErrorCodes import getErrorExitBoolCode, getErrorExitCode, getReleaseCode
from .PythonAPICodes import (
    generateCAPIObjectCode,
    generateCAPIObjectCode0,
    makeArgDescFromExpression,
)


def generateAssignmentAttributeCode(statement, emit, context):
    lookup_source = statement.subnode_expression
    attribute_name = statement.getAttributeName()
    value = statement.subnode_source

    value_name = context.allocateTempName("ass_attr_value")
    generateExpressionCode(
        to_name=value_name, expression=value, emit=emit, context=context
    )

    target_name = context.allocateTempName("ass_attr_target")
    generateExpressionCode(
        to_name=target_name, expression=lookup_source, emit=emit, context=context
    )

    with context.withCurrentSourceCodeReference(
        value.getSourceReference()
        if states.is_full_compat
        else statement.getSourceReference()
    ):
        if attribute_name == "__dict__":
            getAttributeAssignmentDictSlotCode(
                target_name=target_name,
                value_name=value_name,
                emit=emit,
                context=context,
            )
        elif attribute_name == "__class__":
            getAttributeAssignmentClassSlotCode(
                target_name=target_name,
                value_name=value_name,
                emit=emit,
                context=context,
            )
        else:
            getAttributeAssignmentCode(
                target_name=target_name,
                value_name=value_name,
                attribute_name=attribute_name,
                emit=emit,
                context=context,
            )


def generateDelAttributeCode(statement, emit, context):
    target_name = context.allocateTempName("attr_del_target")

    generateExpressionCode(
        to_name=target_name,
        expression=statement.subnode_expression,
        emit=emit,
        context=context,
    )

    with context.withCurrentSourceCodeReference(
        statement.subnode_expression.getSourceReference()
        if states.is_full_compat
        else statement.getSourceReference()
    ):
        getAttributeDelCode(
            target_name=target_name,
            attribute_name=context.getConstantCode(
                constant=statement.getAttributeName()
            ),
            emit=emit,
            context=context,
        )


def _getAttributeLookupHelper(attribute_name, context):
    helper_name = "LOOKUP_ATTRIBUTE_SPECIALIZED_%s" % encodePythonIdentifierToC(
        attribute_name
    )

    if not context.hasHelperCode(helper_name):
        template = getTemplateC("nuitka.code_generation", "HelperAttributeLookup.c.j2")
        context.addHelperCode(
            helper_name,
            template.render(
                helper_name=helper_name,
                attribute_name_code=context.getConstantCode(attribute_name),
            ),
        )
        context.addDeclaration(
            helper_name,
            "static PyObject *%s(PyThreadState *tstate, PyObject *source, Nuitka_AttributeCache *cache);"
            % helper_name,
        )

    return helper_name


def _getAttributeCacheName(attribute_name, context):
    """Allocate storage for one attribute cache, for a single lookup in the code.

    An attribute name is often used with more than one type in the same module,
    and sharing an entry between those makes it get refilled all of the time,
    which is slower than not caching at all.
    """

    cache_name = "attribute_cache_%s_%d" % (
        encodePythonIdentifierToC(attribute_name),
        context.allocateAttributeCacheNumber(),
    )

    context.addDeclaration(
        cache_name, "static Nuitka_AttributeCache %s = {0, 0, false};" % cache_name
    )

    return cache_name


def _getAttributeCheckHelper(attribute_name, can_raise, context):
    helper_name = "HAS_ATTRIBUTE_SPECIALIZED_%s_%s" % (
        encodePythonIdentifierToC(attribute_name),
        "RAISING" if can_raise else "BOOL",
    )

    if not context.hasHelperCode(helper_name):
        template = getTemplateC("nuitka.code_generation", "HelperAttributeCheck.c.j2")
        context.addHelperCode(
            helper_name,
            template.render(
                helper_name=helper_name,
                attribute_name_code=context.getConstantCode(attribute_name),
                can_raise=can_raise,
            ),
        )
        context.addDeclaration(
            helper_name,
            "static int %s(PyThreadState *tstate, PyObject *source, Nuitka_AttributeCache *cache);"
            % helper_name,
        )

    return helper_name


def getAttributeLookupCode(
    to_name, source_name, attribute_name, needs_check, emit, context
):
    if python_version >= 0x3C0:
        emit(
            "%s = %s(tstate, %s, &%s);"
            % (
                to_name,
                _getAttributeLookupHelper(attribute_name, context),
                source_name,
                _getAttributeCacheName(attribute_name, context),
            )
        )
    else:
        if attribute_name == "__dict__":
            emit(
                "%s = LOOKUP_ATTRIBUTE_DICT_SLOT(tstate, %s);" % (to_name, source_name)
            )
        elif attribute_name == "__class__":
            emit(
                "%s = LOOKUP_ATTRIBUTE_CLASS_SLOT(tstate, %s);" % (to_name, source_name)
            )
        else:
            emit(
                "%s = LOOKUP_ATTRIBUTE(tstate, %s, %s);"
                % (to_name, source_name, context.getConstantCode(attribute_name))
            )

    getErrorExitCode(
        check_name=to_name,
        release_name=source_name,
        needs_check=needs_check,
        emit=emit,
        context=context,
    )

    context.addCleanupTempName(to_name)


def generateAttributeLookupCode(to_name, expression, emit, context):
    (source_name,) = generateChildExpressionsCode(
        expression=expression,
        emit=emit,
        context=context,
    )

    attribute_name = expression.getAttributeName()

    with withObjectCodeTemporaryAssignment(
        to_name, "attribute_value", expression, emit, context
    ) as value_name:
        with context.withCurrentSourceCodeReference(expression.getSourceReference()):

            getAttributeLookupCode(
                to_name=value_name,
                source_name=source_name,
                attribute_name=attribute_name,
                needs_check=expression.subnode_expression.mayRaiseExceptionAttributeLookup(
                    exception_type=BaseException, attribute_name=attribute_name
                ),
                emit=emit,
                context=context,
            )


def getAttributeAssignmentCode(target_name, attribute_name, value_name, emit, context):
    res_name = context.getBoolResName()

    attribute_name_code = context.getConstantCode(constant=attribute_name)

    if python_version >= 0x3C0:
        emit(
            "%s = Nuitka_SetAttributeCached(tstate, &%s, %s, %s, %s);"
            % (
                res_name,
                _getAttributeCacheName(attribute_name, context),
                target_name,
                attribute_name_code,
                value_name,
            )
        )
    else:
        emit(
            "%s = SET_ATTRIBUTE(tstate, %s, %s, %s);"
            % (res_name, target_name, attribute_name_code, value_name)
        )

    getErrorExitBoolCode(
        condition="%s == false" % res_name,
        release_names=(value_name, target_name, attribute_name_code),
        emit=emit,
        context=context,
    )


def getAttributeAssignmentDictSlotCode(target_name, value_name, emit, context):
    """Code for special case target.__dict__ = value"""

    res_name = context.getBoolResName()

    emit(
        "%s = SET_ATTRIBUTE_DICT_SLOT(tstate, %s, %s);"
        % (res_name, target_name, value_name)
    )

    getErrorExitBoolCode(
        condition="%s == false" % res_name,
        release_names=(value_name, target_name),
        emit=emit,
        context=context,
    )


def getAttributeAssignmentClassSlotCode(target_name, value_name, emit, context):
    """Get code for special case target.__class__ = value"""

    res_name = context.getBoolResName()

    emit(
        "%s = SET_ATTRIBUTE_CLASS_SLOT(tstate, %s, %s);"
        % (res_name, target_name, value_name)
    )

    getErrorExitBoolCode(
        condition="%s == false" % res_name,
        release_names=(value_name, target_name),
        emit=emit,
        context=context,
    )


def getAttributeDelCode(target_name, attribute_name, emit, context):
    res_name = context.getIntResName()

    emit("%s = PyObject_DelAttr(%s, %s);" % (res_name, target_name, attribute_name))

    getErrorExitBoolCode(
        condition="%s == -1" % res_name,
        release_names=(target_name, attribute_name),
        emit=emit,
        context=context,
    )


def generateAttributeLookupSpecialCode(to_name, expression, emit, context):
    (source_name,) = generateChildExpressionsCode(
        expression=expression, emit=emit, context=context
    )

    attribute_name = expression.getAttributeName()

    getAttributeLookupSpecialCode(
        to_name=to_name,
        source_name=source_name,
        attr_name=context.getConstantCode(constant=attribute_name),
        needs_check=expression.subnode_expression.mayRaiseExceptionAttributeLookupSpecial(
            exception_type=BaseException, attribute_name=attribute_name
        ),
        emit=emit,
        context=context,
    )


def getAttributeLookupSpecialCode(
    to_name, source_name, attr_name, needs_check, emit, context
):
    emit("%s = LOOKUP_SPECIAL(tstate, %s, %s);" % (to_name, source_name, attr_name))

    getErrorExitCode(
        check_name=to_name,
        release_names=(source_name, attr_name),
        emit=emit,
        needs_check=needs_check,
        context=context,
    )

    context.addCleanupTempName(to_name)


def generateBuiltinHasattrCode(to_name, expression, emit, context):
    source_name, attr_name = generateChildExpressionsCode(
        expression=expression, emit=emit, context=context
    )

    res_name = context.getIntResName()

    if (
        python_version >= 0x3C0
        and expression.subnode_name.isCompileTimeConstant()
        and type(expression.subnode_name.getCompileTimeConstant()) is str
    ):
        attribute_name = expression.subnode_name.getCompileTimeConstant()
        emit(
            "%s = %s(tstate, %s, &%s);"
            % (
                res_name,
                _getAttributeCheckHelper(attribute_name, True, context),
                source_name,
                _getAttributeCacheName(attribute_name, context),
            )
        )
    else:
        emit(
            "%s = BUILTIN_HASATTR_BOOL(tstate, %s, %s);"
            % (res_name, source_name, attr_name)
        )

    getErrorExitBoolCode(
        condition="%s == -1" % res_name,
        release_names=(source_name, attr_name),
        needs_check=expression.mayRaiseException(BaseException),
        emit=emit,
        context=context,
    )

    to_name.getCType().emitAssignmentCodeFromBoolCondition(
        to_name=to_name, condition="%s != 0" % res_name, emit=emit
    )


def generateAttributeCheckCode(to_name, expression, emit, context):
    (source_name,) = generateChildExpressionsCode(
        expression=expression, emit=emit, context=context
    )

    if python_version >= 0x3C0:
        can_raise = expression.mayRaiseExceptionOperation()
        res_name = context.getIntResName()

        emit(
            "%s = %s(tstate, %s, &%s);"
            % (
                res_name,
                _getAttributeCheckHelper(
                    expression.getAttributeName(), can_raise, context
                ),
                source_name,
                _getAttributeCacheName(expression.getAttributeName(), context),
            )
        )

        getErrorExitBoolCode(
            condition="%s == -1" % res_name,
            release_name=source_name,
            emit=emit,
            context=context,
        )

        to_name.getCType().emitAssignmentCodeFromBoolCondition(
            to_name=to_name, condition="%s != 0" % res_name, emit=emit
        )
    elif expression.mayRaiseExceptionOperation():
        res_name = context.getIntResName()

        emit(
            "%s = HAS_ATTR_BOOL2(tstate, %s, %s);"
            % (
                res_name,
                source_name,
                context.getConstantCode(constant=expression.getAttributeName()),
            )
        )

        getErrorExitBoolCode(
            condition="%s == -1" % res_name,
            release_name=source_name,
            emit=emit,
            context=context,
        )

        to_name.getCType().emitAssignmentCodeFromBoolCondition(
            to_name=to_name, condition="%s != 0" % res_name, emit=emit
        )
    else:
        res_name = context.getBoolResName()

        emit(
            "%s = HAS_ATTR_BOOL(tstate, %s, %s);"
            % (
                res_name,
                source_name,
                context.getConstantCode(constant=expression.getAttributeName()),
            )
        )

        getReleaseCode(release_name=source_name, emit=emit, context=context)

        to_name.getCType().emitAssignmentCodeFromBoolCondition(
            to_name=to_name, condition=res_name, emit=emit
        )


def generateBuiltinGetattrCode(to_name, expression, emit, context):
    generateCAPIObjectCode(
        to_name=to_name,
        capi="BUILTIN_GETATTR",
        tstate=True,
        arg_desc=makeArgDescFromExpression(expression),
        may_raise=expression.mayRaiseException(BaseException),
        conversion_check=decideConversionCheckNeeded(to_name, expression),
        source_ref=expression.getCompatibleSourceReference(),
        none_null=True,
        emit=emit,
        context=context,
    )


def generateBuiltinSetattrCode(to_name, expression, emit, context):
    generateCAPIObjectCode0(
        to_name=to_name,
        capi="BUILTIN_SETATTR",
        tstate=False,
        arg_desc=makeArgDescFromExpression(expression),
        may_raise=expression.mayRaiseException(BaseException),
        conversion_check=decideConversionCheckNeeded(to_name, expression),
        source_ref=expression.getCompatibleSourceReference(),
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
