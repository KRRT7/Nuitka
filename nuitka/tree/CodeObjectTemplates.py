#     Copyright 2026, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file

"""Helpers to preserve CPython code object metadata."""

import types

from nuitka.PythonVersions import python_version

from .SourceHandling import readSourceCodeFromFilename

_compiled_source_cache = {}
_compiled_source_match_counts = {}


def _getCompiledModuleCode(filename):
    if filename not in _compiled_source_cache:
        try:
            source_code = readSourceCodeFromFilename(None, filename)
            compiled_code = compile(source_code, filename, "exec")
        except Exception:
            compiled_code = None

        _compiled_source_cache[filename] = compiled_code

    return _compiled_source_cache[filename]


def _iterNestedCodeObjects(code_object):
    for constant in code_object.co_consts:
        if type(constant) is types.CodeType:
            yield constant
            yield from _iterNestedCodeObjects(constant)


def attachCodeObjectTemplate(code_object):
    if python_version < 0x3B0:
        return

    compiled_code = _getCompiledModuleCode(code_object.getFilename())

    if compiled_code is None:
        return

    code_name = code_object.getCodeObjectName()
    code_qualname = code_object.getCodeObjectQualname()
    line_number = code_object.getLineNumber()

    matching = []
    fallback = []
    name_fallback = []

    for candidate in _iterNestedCodeObjects(compiled_code):
        if candidate.co_name != code_name:
            continue

        name_fallback.append(candidate)

        if candidate.co_firstlineno != line_number:
            continue

        if candidate.co_qualname == code_qualname:
            matching.append(candidate)
        else:
            fallback.append(candidate)

    if matching:
        key = (code_object.getFilename(), code_name, code_qualname, line_number)
        count = _compiled_source_match_counts.get(key, 0)

        if count < len(matching):
            code_object.setCodeTemplate(matching[count])
            _compiled_source_match_counts[key] = count + 1

            return

    if fallback:
        key = (code_object.getFilename(), code_name, None, line_number)
        count = _compiled_source_match_counts.get(key, 0)

        if count < len(fallback):
            code_object.setCodeTemplate(fallback[count])
            _compiled_source_match_counts[key] = count + 1

            return

    if name_fallback:
        key = (code_object.getFilename(), code_name, "__name_only__")
        count = _compiled_source_match_counts.get(key, 0)

        if count < len(name_fallback):
            code_object.setCodeTemplate(name_fallback[count])
            _compiled_source_match_counts[key] = count + 1
