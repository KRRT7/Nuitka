#     Copyright 2025, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file


""" XML node tree handling

Means to create XML elements from Nuitka tree nodes and to convert the
XML tree to ASCII or output it.
"""

import os

from nuitka.__past__ import BytesIO, StringIO, basestring


def _indent(elem, level=0, more_sibs=False):
    if level:
        indent_str = "\n" + (level - 1) * "  "
    else:
        indent_str = "\n"

    num_kids = len(elem)
    if num_kids:
        # Only conditionally strip text if required, avoiding repeated strip calls
        text = elem.text
        if text is None or not text.strip():
            # Efficiently precompute new text
            if level:
                elem.text = indent_str + "    "
            else:
                elem.text = indent_str + "  "
        # Use enumerate instead of count/index logic for efficiency
        for idx, kid in enumerate(elem):
            # Only True for siblings before the last
            _indent(kid, level + 1, idx < num_kids - 1)
        # Only conditionally strip tail if required
        tail = elem.tail
        if tail is None or not tail.strip():
            # Build tail string efficiently
            if more_sibs:
                elem.tail = indent_str + "  "
            else:
                elem.tail = indent_str
    else:
        # Only check tail if required, as in original
        if level:
            tail = elem.tail
            if tail is None or not tail.strip():
                if more_sibs:
                    elem.tail = indent_str + "  "
                else:
                    elem.tail = indent_str


    return elem


def _dedent(elem, level=0):
    if not elem.text or not elem.text.strip():
        elem.text = ""

    for child in elem:
        _dedent(child, level + 1)

    if not elem.tail or not elem.tail.strip():
        elem.tail = ""

    return elem


try:
    import xml.etree.ElementTree

    xml_module = xml.etree.ElementTree

    Element = xml.etree.ElementTree.Element

    def xml_tostring(tree, indent=True, encoding=None):
        if indent:
            _indent(tree)
        elif not indent:
            _dedent(tree)

        return xml_module.tostring(tree, encoding=encoding)

except ImportError:
    xml_module = None
    Element = None
    xml_tostring = None

# TODO: Use the writer to create the XML we output. That should be more
# scalable and/or faster.
# try:
#     from lxml import (
#         xmlfile as xml_writer,  # pylint: disable=I0021,import-error,unused-import
#     )
# except ImportError:
#     xml_writer = None


def toBytes(tree, indent=True, encoding=None):
    return xml_tostring(tree, indent=indent, encoding=encoding)


def toString(tree):
    result = toBytes(tree, encoding="utf8")

    if str is not bytes:
        result = result.decode("utf8")

    return result


def fromString(text, use_lxml=False):
    if type(text) is str:
        return fromFile(StringIO(text), use_lxml=use_lxml)
    else:
        return fromFile(BytesIO(text), use_lxml=use_lxml)


def fromFile(file_handle, use_lxml=False):
    if isinstance(file_handle, basestring):
        if not os.path.isfile(file_handle):
            return None

    if use_lxml:
        from lxml import etree  # pylint: disable=I0021,import-error

        # TODO: Catch parse error exception to return None as well.
        return etree.parse(file_handle).getroot()
    else:
        try:
            return xml_module.parse(file_handle).getroot()
        except xml.etree.ElementTree.ParseError:
            return None


def appendTreeElement(parent, *args, **kwargs):
    element = Element(*args, **kwargs)

    parent.append(element)

    return element


def dumpTreeXMLToFile(tree, output_file):
    """Write an XML node tree to a file."""

    value = toBytes(tree).rstrip()
    output_file.write(value)
    output_file.write(b"\n")


#     Part of "Nuitka", an optimizing Python compiler that is compatible and
#     integrates with CPython, but also works on its own.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
