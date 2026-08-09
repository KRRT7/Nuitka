#     Copyright 2026, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file


"""CType classes for nuitka_ilong, a struct to represent long values."""

from nuitka.code_generation.templates.CodeTemplatesVariables import (
    template_release_object_clear,
    template_release_object_unclear,
)
from nuitka.PythonVersions import isPythonValidCLongValue

from ..ErrorCodes import getErrorExitBoolCode, getTakeReferenceCode
from .CTypeBases import CTypeBase


class CTypeNuitkaIntOrLongStruct(CTypeBase):
    c_type = "nuitka_ilong"

    helper_code = "NILONG"

    @classmethod
    def isDualType(cls):
        return True

    @classmethod
    def emitVariableAssignCode(
        cls, value_name, needs_release, tmp_name, ref_count, inplace, emit, context
    ):
        if inplace:
            # The in-place helper was handed the reference of the variable and
            # left one in its place, either by updating the object it was given
            # or by releasing it and making a new one. So there is nothing to
            # take here, and releasing the old value would release what the
            # helper already did, or what another user of the value still owns.
            if tmp_name.c_type == cls.c_type:
                emit("%s = %s;" % (value_name, tmp_name))
            else:
                emit("%s = Nuitka_NILONG_FromObject(%s);" % (value_name, tmp_name))

            if ref_count:
                context.removeCleanupTempName(tmp_name)

            return

        if not ref_count:
            getTakeReferenceCode(tmp_name, emit)

        def emitAssignCode():
            if tmp_name.c_type == cls.c_type:
                emit("%s = %s;" % (value_name, tmp_name))
            elif tmp_name.c_type == "PyObject *":
                emit("%s = Nuitka_NILONG_FromObject(%s);" % (value_name, tmp_name))
            else:
                # Other C types know how to convert themselves to this one.
                cls.emitAssignConversionCode(
                    to_name=value_name,
                    value_name=tmp_name,
                    needs_check=False,
                    emit=emit,
                    context=context,
                )

        if needs_release is False:
            emitAssignCode()
        else:
            # Keep the old value alive until the new one is in place, in case
            # they are the very same value.
            emit("{")
            emit("nuitka_ilong old = %s;" % value_name)
            emitAssignCode()
            emit("RELEASE_NILONG_VALUE(&old);")
            emit("}")

        if ref_count:
            context.removeCleanupTempName(tmp_name)

    @classmethod
    def emitVariantAssignmentCode(
        cls, to_name, ilong_value_name, int_value, emit, context
    ):
        if ilong_value_name is None:
            # Only the C value is known, no object for it was made, and none
            # has to be, it is created on demand only.
            assert int_value is not None

            emit("SET_NILONG_C_VALUE(&%s, %s);" % (to_name, int_value))
        else:
            if int_value is None:
                emit("SET_NILONG_OBJECT_VALUE(&%s, %s);" % (to_name, ilong_value_name))
            else:
                emit(
                    "SET_NILONG_OBJECT_AND_C_VALUE(&%s, %s, %s );"
                    % (to_name, ilong_value_name, int_value)
                )

            context.transferCleanupTempName(ilong_value_name, to_name)

    @classmethod
    def getTruthCheckCode(cls, value_name):
        return (
            "IS_NILONG_C_VALUE_VALID(&%s) ? %s.c_value != 0 : CHECK_IF_TRUE(%s.python_value) == 1"
            % (
                value_name,
                value_name,
                value_name,
            )
        )

    @classmethod
    def emitValueAccessCode(cls, value_name, emit, context):
        # Nothing to do for this type, pylint: disable=unused-argument
        return value_name

    @classmethod
    def emitValueAssertionCode(cls, value_name, emit):
        emit("assert(%s.validity != NUITKA_ILONG_UNASSIGNED);" % value_name)

    @classmethod
    def emitAssignConversionCode(cls, to_name, value_name, needs_check, emit, context):
        if value_name.c_type == cls.c_type:
            emit("%s = %s;" % (to_name, value_name))

            # A reference owned by the source value becomes owned by the
            # target, this is not doing anything for borrowed ones.
            context.transferCleanupTempName(value_name, to_name)
        else:
            value_name.getCType().emitAssignmentCodeToNuitkaIntOrLong(
                to_name=to_name,
                value_name=value_name,
                needs_check=needs_check,
                emit=emit,
                context=context,
            )

    @classmethod
    def emitAssignmentCodeToNuitkaIntOrLong(
        cls, to_name, value_name, needs_check, emit, context
    ):
        # Same type, so nothing to convert, ownership is passed along.
        # pylint: disable=unused-argument
        emit("%s = %s;" % (to_name, value_name))

        context.transferCleanupTempName(value_name, to_name)

    @classmethod
    def emitAssignmentCodeToNuitkaBool(
        cls, to_name, value_name, needs_check, emit, context
    ):
        truth_name = context.allocateTempName("truth_name", "int")

        emit("if (IS_NILONG_C_VALUE_VALID(&%s)) {" % value_name)
        emit("%s = %s.c_value != 0;" % (truth_name, value_name))
        emit("} else {")
        emit("%s = CHECK_IF_TRUE(%s.python_value);" % (truth_name, value_name))
        emit("}")

        getErrorExitBoolCode(
            condition="%s == -1" % truth_name,
            needs_check=needs_check,
            emit=emit,
            context=context,
        )

        emit(
            "%s = %s == 0 ? NUITKA_BOOL_FALSE : NUITKA_BOOL_TRUE;"
            % (to_name, truth_name)
        )

    @classmethod
    def getInitValue(cls, init_from):
        if init_from is None:
            # TODO: In debug mode, use more crash prone maybe.
            return "(nuitka_ilong){NUITKA_ILONG_UNASSIGNED, NULL, 0}"
        else:
            return "Nuitka_NILONG_FromObject(%s)" % init_from

    @classmethod
    def getInitTestConditionCode(cls, value_name, inverted):
        return "%s.validity %s NUITKA_ILONG_UNASSIGNED" % (
            value_name,
            "==" if inverted else "!=",
        )

    @classmethod
    def hasReleaseCode(cls):
        return True

    @classmethod
    def getReleaseCode(cls, value_name, needs_check, emit):
        emit(
            "if ((%s.validity & NUITKA_ILONG_OBJECT_VALID) == NUITKA_ILONG_OBJECT_VALID) {"
            % value_name
        )

        # TODO: Have a derived C type that does it.

        if needs_check:
            template = template_release_object_unclear
        else:
            template = template_release_object_clear

        emit(template % {"identifier": "%s.python_value" % value_name})

        emit("}")

    @classmethod
    def getDeleteObjectCode(
        cls, to_name, value_name, needs_check, tolerant, emit, context
    ):
        if not needs_check:
            emit("RELEASE_NILONG_VALUE(&%s);" % value_name)
        elif tolerant:
            emit("RELEASE_NILONG_VALUE(&%s);" % value_name)
        else:
            # TODO: That doesn't seem right, maybe this function makes no sense
            # after all, and should be one for checking, and one for releasing
            # instead.
            emit("%s = %s.validity != NUITKA_ILONG_UNASSIGNED;" % (to_name, value_name))
            emit("RELEASE_NILONG_VALUE(&%s);" % value_name)

    @classmethod
    def emitAssignmentCodeFromBoolCondition(cls, to_name, condition, emit):
        # The boolean values are the small integers 0 and 1, for which both
        # the object and the C value are immediately available.
        emit(
            "SET_NILONG_BOOL_VALUE(&%(to_name)s, %(condition)s);"
            % {"to_name": to_name, "condition": condition}
        )

    @classmethod
    def emitAssignmentCodeFromConstant(
        cls, to_name, constant, may_escape, emit, context
    ):
        # No escaping matters with integer values, as they are immutable
        # the do not have to make copies of the prepared values.
        # pylint: disable=unused-argument

        assert type(constant) is int, repr(constant)

        ilong_value_name = context.getConstantCode(constant=constant)

        if isPythonValidCLongValue(constant):
            cls.emitVariantAssignmentCode(
                to_name=to_name,
                ilong_value_name=ilong_value_name,
                int_value=constant,
                emit=emit,
                context=context,
            )
        else:
            emit("SET_NILONG_OBJECT_VALUE(&%s, %s);" % (to_name, ilong_value_name))
            context.transferCleanupTempName(ilong_value_name, to_name)

    @classmethod
    def getTakeReferenceCode(cls, value_name, emit):
        """Take reference code for given object."""

        emit("INCREF_NILONG_VALUE(&%s);" % value_name)

    @classmethod
    def emitReInitCode(cls, value_name, emit):
        emit("%s.validity = NUITKA_ILONG_UNASSIGNED;" % value_name)

    @classmethod
    def hasErrorIndicator(cls):
        return True

    @classmethod
    def getExceptionCheckCondition(cls, value_name):
        # Note: Nothing is putting this validity in place yet, the helper
        # functions for this type indicate errors with a "bool" return value
        # instead, so this is not actually reached at this time.
        return "%s.validity == NUITKA_ILONG_EXCEPTION" % value_name


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
