#     Copyright 2026, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file


"""Generate code that updates the source code line."""


def getCurrentLineNumberCode(context):
    frame_handle = context.getFrameHandle()

    if frame_handle is None:
        return ""
    else:
        source_ref = context.getCurrentSourceCodeReference()

        if source_ref.isInternal():
            return ""
        else:
            return str(source_ref.getLineNumber())


def getLineNumberUpdateCode(context, allow_backward=True):
    lineno_value = getCurrentLineNumberCode(context)

    if lineno_value:
        frame_handle = context.getFrameHandle()
        exception_exit = context.getExceptionEscape()

        if exception_exit is not None:
            (
                exception_state_name,
                exception_lineno,
            ) = context.variable_storage.getExceptionVariableDescriptions()

            code = """\
if (Nuitka_Frame_TraceLine(tstate, %(frame_handle)s, %(lineno_value)s) < 0) {
    FETCH_ERROR_OCCURRED_STATE(tstate, &%(exception_state_name)s);

	%(exception_lineno)s = %(lineno_value)s;
	    goto %(exception_exit)s;
	}
	if (Nuitka_Frame_TraceOpcode(tstate, %(frame_handle)s, %(lineno_value)s) < 0) {
	    FETCH_ERROR_OCCURRED_STATE(tstate, &%(exception_state_name)s);

	%(exception_lineno)s = %(lineno_value)s;
	    goto %(exception_exit)s;
	}
		Nuitka_Frame_SetLineNumber(%(frame_handle)s, %(lineno_value)s);""" % {
                "frame_handle": frame_handle,
                "lineno_value": lineno_value,
                "exception_exit": exception_exit,
                "exception_state_name": exception_state_name,
                "exception_lineno": exception_lineno,
            }

            if allow_backward:
                return code
            else:
                return """\
if (%(lineno_value)s > Nuitka_GetFrameLineNumber(%(frame_handle)s)) {
%(code)s
}""" % {
                    "frame_handle": frame_handle,
                    "lineno_value": lineno_value,
                    "code": code,
                }
        else:
            code = "Nuitka_Frame_SetLineNumber(%s, %s);" % (
                frame_handle,
                lineno_value,
            )

            if allow_backward:
                return code
            else:
                return """\
if (%(lineno_value)s > Nuitka_GetFrameLineNumber(%(frame_handle)s)) {
    %(code)s
}""" % {
                    "frame_handle": frame_handle,
                    "lineno_value": lineno_value,
                    "code": code,
                }
    else:
        return ""


def getErrorLineNumberUpdateCode(context):
    (
        _exception_state,
        exception_lineno,
    ) = context.variable_storage.getExceptionVariableDescriptions()

    lineno_value = getCurrentLineNumberCode(context)

    if lineno_value:
        return "%s = %s;" % (exception_lineno, lineno_value)
    else:
        return ""


def emitErrorLineNumberUpdateCode(emit, context):
    update_code = getErrorLineNumberUpdateCode(context)

    if update_code:
        emit(update_code)


def emitLineNumberUpdateCode(expression, emit, context):
    # Optional expression.
    if expression is not None:
        context.setCurrentSourceCodeReference(expression.getCompatibleSourceReference())

    code = getLineNumberUpdateCode(context)

    if code:
        emit(code)


def emitLineNumberUpdateCodeForReturn(statement, emit, context):
    source_ref = statement.getCompatibleSourceReference()

    if source_ref.isInternal():
        return

    frame_handle = context.getFrameHandle()
    exception_exit = context.getExceptionEscape()

    if frame_handle is not None and exception_exit is not None:
        (
            exception_state_name,
            exception_lineno,
        ) = context.variable_storage.getExceptionVariableDescriptions()

        lineno_value = str(source_ref.getLineNumber())

        emit(
            """\
if (Nuitka_Frame_TraceLinesToLine(tstate, %(frame_handle)s, %(lineno_value)s) < 0) {
    FETCH_ERROR_OCCURRED_STATE(tstate, &%(exception_state_name)s);

%(exception_lineno)s = Nuitka_GetFrameLineNumber(%(frame_handle)s);
    goto %(exception_exit)s;
}"""
            % {
                "frame_handle": frame_handle,
                "lineno_value": lineno_value,
                "exception_exit": exception_exit,
                "exception_state_name": exception_state_name,
                "exception_lineno": exception_lineno,
            }
        )

    context.setCurrentSourceCodeReference(source_ref)

    code = getLineNumberUpdateCode(context, allow_backward=False)

    if code:
        emit(code)


def generateFrameLineUpdateCode(statement, emit, context):
    emitLineNumberUpdateCode(statement, emit, context)


def getSetLineNumberCodeRaw(to_name, emit, context):
    assert context.getFrameHandle() is not None

    emit("Nuitka_Frame_SetLineNumber(%s, %s);" % (context.getFrameHandle(), to_name))


def getLineNumberCode(to_name, emit, context):
    assert context.getFrameHandle() is not None

    emit("%s = %s->m_frame.f_lineno;" % (to_name, context.getFrameHandle()))


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
