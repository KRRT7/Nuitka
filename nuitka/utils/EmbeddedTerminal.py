#     Copyright 2025, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file
#
#     Embedded terminal emulator for macOS app bundles using native Cocoa via ctypes.
#
#     Provides a self-contained terminal when apps are launched from Finder without TTY.

"""
Embedded terminal emulator for macOS app bundles.

When a Nuitka-compiled app is launched from Finder (without a TTY), this module
provides a native Cocoa terminal window that:
1. Creates a PTY (pseudo-terminal)
2. Re-executes the app with the PTY attached
3. Renders the terminal output in a native NSWindow

This allows console/TUI applications to work properly when distributed as .app bundles.
Uses pure ctypes to interface with macOS Cocoa APIs - zero external dependencies.
"""

import fcntl
import os
import platform
import pty
import struct
import subprocess
import sys
import termios
from ctypes import (
    CDLL,
    CFUNCTYPE,
    POINTER,
    Structure,
    c_bool,
    c_char_p,
    c_double,
    c_int,
    c_long,
    c_uint,
    c_ulong,
    c_void_p,
    sizeof,
    util,
)

# =============================================================================
# Objective-C Runtime Bindings
# =============================================================================


def _load_library(name):
    """Load a dynamic library with Big Sur+ fallback."""
    # Try standard lookup first
    path = util.find_library(name)
    if path:
        return CDLL(path)

    # Fallback paths for newer macOS versions where find_library may fail
    fallback_paths = [
        "/usr/lib/lib%s.dylib" % name,
        "/System/Library/Frameworks/%s.framework/%s" % (name, name),
    ]

    for fallback in fallback_paths:
        try:
            return CDLL(fallback)
        except OSError:
            pass

    raise OSError("Cannot load library: %s" % name)


# Load Objective-C runtime
_libobjc = _load_library("objc")

# Load AppKit framework (contains NSApplication, NSWindow, etc.)
# This must be loaded before we can access Cocoa classes
try:
    _appkit = CDLL("/System/Library/Frameworks/AppKit.framework/AppKit")
except OSError:
    _appkit = None

# Load Foundation framework (contains NSString, NSRunLoop, etc.)
try:
    _foundation = CDLL("/System/Library/Frameworks/Foundation.framework/Foundation")
except OSError:
    _foundation = None

# Core runtime functions
_objc_getClass = _libobjc.objc_getClass
_objc_getClass.argtypes = [c_char_p]
_objc_getClass.restype = c_void_p

_sel_registerName = _libobjc.sel_registerName
_sel_registerName.argtypes = [c_char_p]
_sel_registerName.restype = c_void_p

_objc_msgSend = _libobjc.objc_msgSend

# Architecture detection
_is_arm64 = platform.machine() == "arm64"


def _get_class(name):
    """Get an Objective-C class by name."""
    cls = _objc_getClass(name if isinstance(name, bytes) else name.encode())
    if not cls:
        raise RuntimeError("Cannot find Objective-C class: %s" % name)
    return cls


def _get_selector(name):
    """Get a selector by name."""
    return _sel_registerName(name if isinstance(name, bytes) else name.encode())


def _send_message(receiver, selector, *args, restype=c_void_p, argtypes=None):
    """Send an Objective-C message."""
    if argtypes is None:
        argtypes = []

    # Configure objc_msgSend for this specific call
    _objc_msgSend.restype = restype
    _objc_msgSend.argtypes = [c_void_p, c_void_p] + list(argtypes)

    sel = _get_selector(selector)
    return _objc_msgSend(receiver, sel, *args)


def _send_message_stret(receiver, selector, *args, restype=None, argtypes=None):
    """Send an Objective-C message that returns a structure (x86_64 only)."""
    if argtypes is None:
        argtypes = []

    if _is_arm64:
        # ARM64 doesn't need stret for most structures
        return _send_message(
            receiver, selector, *args, restype=restype, argtypes=argtypes
        )

    # x86_64: structures > 16 bytes need objc_msgSend_stret
    _libobjc.objc_msgSend_stret.restype = None
    _libobjc.objc_msgSend_stret.argtypes = [
        POINTER(restype),
        c_void_p,
        c_void_p,
    ] + list(argtypes)

    result = restype()
    sel = _get_selector(selector)
    _libobjc.objc_msgSend_stret(result, receiver, sel, *args)
    return result


# =============================================================================
# Cocoa Type Definitions
# =============================================================================


class NSPoint(Structure):
    _fields_ = [("x", c_double), ("y", c_double)]


class NSSize(Structure):
    _fields_ = [("width", c_double), ("height", c_double)]


class NSRect(Structure):
    _fields_ = [("origin", NSPoint), ("size", NSSize)]

    @classmethod
    def make(cls, x, y, width, height):
        return cls(NSPoint(x, y), NSSize(width, height))


class NSRange(Structure):
    _fields_ = [("location", c_ulong), ("length", c_ulong)]


# NSWindow style masks
NSWindowStyleMaskTitled = 1 << 0
NSWindowStyleMaskClosable = 1 << 1
NSWindowStyleMaskMiniaturizable = 1 << 2
NSWindowStyleMaskResizable = 1 << 3
NSWindowStyleMaskDefault = (
    NSWindowStyleMaskTitled
    | NSWindowStyleMaskClosable
    | NSWindowStyleMaskMiniaturizable
    | NSWindowStyleMaskResizable
)

# NSBackingStoreType
NSBackingStoreBuffered = 2

# NSApplicationActivationPolicy
NSApplicationActivationPolicyRegular = 0


# =============================================================================
# NSString Helper
# =============================================================================


def _create_nsstring(text):
    """Create an NSString from a Python string."""
    NSString = _get_class(b"NSString")
    string = _send_message(NSString, b"alloc")
    string = _send_message(
        string,
        b"initWithUTF8String:",
        text.encode("utf8") if isinstance(text, str) else text,
        argtypes=[c_char_p],
    )
    return string


def _get_nsstring_value(nsstring):
    """Get Python string from NSString."""
    _objc_msgSend.restype = c_char_p
    _objc_msgSend.argtypes = [c_void_p, c_void_p]
    sel = _get_selector(b"UTF8String")
    result = _objc_msgSend(nsstring, sel)
    return result.decode("utf8") if result else ""


# =============================================================================
# Terminal Constants (from bittty/constants.py)
# =============================================================================

# Erase modes (for ED and EL)
ERASE_FROM_CURSOR_TO_END = 0
ERASE_FROM_START_TO_CURSOR = 1
ERASE_ALL = 2

# C0 Control Characters
BEL = "\x07"
BS = "\x08"
HT = "\x09"
LF = "\x0a"
VT = "\x0b"
FF = "\x0c"
CR = "\x0d"
SO = "\x0e"
SI = "\x0f"
ESC = "\x1b"
DEL = "\x7f"

# C1 Control Characters (8-bit)
C1_IND = "\x84"  # Index (same as ESC D)
C1_NEL = "\x85"  # Next Line (same as ESC E)
C1_HTS = "\x88"  # Horizontal Tab Set (same as ESC H)
C1_RI = "\x8d"  # Reverse Index (same as ESC M)
C1_SS2 = "\x8e"  # Single Shift 2 (same as ESC N)
C1_SS3 = "\x8f"  # Single Shift 3 (same as ESC O)
C1_DCS = "\x90"  # Device Control String (same as ESC P)
C1_SPA = "\x96"  # Start of Protected Area
C1_EPA = "\x97"  # End of Protected Area
C1_SOS = "\x98"  # Start of String (same as ESC X)
C1_CSI = "\x9b"  # Control Sequence Introducer (same as ESC [)
C1_ST = "\x9c"  # String Terminator (same as ESC \)
C1_OSC = "\x9d"  # Operating System Command (same as ESC ])
C1_PM = "\x9e"  # Privacy Message (same as ESC ^)
C1_APC = "\x9f"  # Application Program Command (same as ESC _)

# Default terminal dimensions
DEFAULT_TERMINAL_WIDTH = 80
DEFAULT_TERMINAL_HEIGHT = 24


# =============================================================================
# Character Sets (from bittty/charsets.py)
# =============================================================================

# DEC Special Graphics (ESC ( 0) - Box drawing and special symbols
DEC_SPECIAL_GRAPHICS = {
    "j": "\u2518",  # Lower right corner
    "k": "\u2510",  # Upper right corner
    "l": "\u250c",  # Upper left corner
    "m": "\u2514",  # Lower left corner
    "n": "\u253c",  # Crossing lines
    "q": "\u2500",  # Horizontal line
    "t": "\u251c",  # Left T
    "u": "\u2524",  # Right T
    "v": "\u2534",  # Bottom T
    "w": "\u252c",  # Top T
    "x": "\u2502",  # Vertical line
    "a": "\u2592",  # Checkerboard
    "`": "\u25c6",  # Diamond
    "f": "\u00b0",  # Degree symbol
    "g": "\u00b1",  # Plus/minus
    "~": "\u00b7",  # Bullet
    "0": "\u2588",  # Solid block
}

CHARSETS = {
    "A": {},  # UK National
    "B": {},  # US ASCII (no changes)
    "0": DEC_SPECIAL_GRAPHICS,
    "1": {},  # Alternate ROM
    "2": {},  # Alternate ROM Special Graphics
}


def _get_charset(designator):
    """Get character set mapping for a designator."""
    return CHARSETS.get(designator, {})


# =============================================================================
# Style Classes (from bittty/style.py)
# =============================================================================


class Color(object):
    """Represents a terminal color."""

    def __init__(self, mode, value=None):
        # mode: "default", "indexed", or "rgb"
        self.mode = mode
        self.value = value

    def __eq__(self, other):
        if not isinstance(other, Color):
            return False
        return self.mode == other.mode and self.value == other.value

    def __hash__(self):
        if self.mode == "rgb" and self.value is not None:
            return hash((self.mode, tuple(self.value)))
        return hash((self.mode, self.value))

    def get_ansi(self):
        if self.mode == "default":
            return ""
        elif self.mode == "indexed":
            return "5;%d" % self.value
        elif self.mode == "rgb":
            r, g, b = self.value
            return "2;%d;%d;%d" % (r, g, b)
        return ""


class Style(object):
    """Represents text style attributes."""

    def __init__(
        self,
        fg=None,
        bg=None,
        bold=None,
        dim=None,
        italic=None,
        underline=None,
        blink=None,
        reverse=None,
        conceal=None,
        strike=None,
    ):
        self.fg = fg
        self.bg = bg
        self.bold = bold
        self.dim = dim
        self.italic = italic
        self.underline = underline
        self.blink = blink
        self.reverse = reverse
        self.conceal = conceal
        self.strike = strike

    def __eq__(self, other):
        if not isinstance(other, Style):
            return False
        return (
            self.fg == other.fg
            and self.bg == other.bg
            and self.bold == other.bold
            and self.dim == other.dim
            and self.italic == other.italic
            and self.underline == other.underline
            and self.blink == other.blink
            and self.reverse == other.reverse
            and self.conceal == other.conceal
            and self.strike == other.strike
        )

    def __hash__(self):
        return hash(
            (
                self.fg,
                self.bg,
                self.bold,
                self.dim,
                self.italic,
                self.underline,
                self.blink,
                self.reverse,
                self.conceal,
                self.strike,
            )
        )

    def copy(self, **kwargs):
        """Create a copy with optional attribute changes."""
        return Style(
            fg=kwargs.get("fg", self.fg),
            bg=kwargs.get("bg", self.bg),
            bold=kwargs.get("bold", self.bold),
            dim=kwargs.get("dim", self.dim),
            italic=kwargs.get("italic", self.italic),
            underline=kwargs.get("underline", self.underline),
            blink=kwargs.get("blink", self.blink),
            reverse=kwargs.get("reverse", self.reverse),
            conceal=kwargs.get("conceal", self.conceal),
            strike=kwargs.get("strike", self.strike),
        )

    def merge(self, other):
        """Merge another style into this one. The other style takes precedence."""

        def merge_attr(base_attr, other_attr):
            if other_attr is not None:
                return other_attr
            return base_attr

        return Style(
            fg=other.fg if other.fg is not None else self.fg,
            bg=other.bg if other.bg is not None else self.bg,
            bold=merge_attr(self.bold, other.bold),
            dim=merge_attr(self.dim, other.dim),
            italic=merge_attr(self.italic, other.italic),
            underline=merge_attr(self.underline, other.underline),
            blink=merge_attr(self.blink, other.blink),
            reverse=merge_attr(self.reverse, other.reverse),
            conceal=merge_attr(self.conceal, other.conceal),
            strike=merge_attr(self.strike, other.strike),
        )

    def diff(self, other):
        """Generate minimal ANSI sequence to transition to another style."""
        if self == other:
            return ""
        if other == Style():
            return "\x1b[0m"
        if self == Style():
            return _style_to_ansi(other)
        target_ansi = _style_to_ansi(other)
        return "\x1b[0m%s" % target_ansi if target_ansi else "\x1b[0m"


def _parse_sgr_sequence(ansi):
    """Parse an SGR ANSI sequence into a Style object."""
    if not ansi.startswith("\x1b[") or not ansi.endswith("m"):
        return Style()

    tokens = ansi[2:-1].split(";")
    return _interpret_sgr_tokens(tuple(tokens))


def _interpret_sgr_tokens(tokens):
    """Interpret SGR tokens into a Style object."""
    style = Style()
    i = 0
    while i < len(tokens):
        token = tokens[i]

        if token in ("0", "00"):
            style = Style()
        elif token in ("1", "01"):
            style = style.copy(bold=True)
        elif token == "2":
            style = style.copy(dim=True)
        elif token == "3":
            style = style.copy(italic=True)
        elif token == "4":
            style = style.copy(underline=True)
        elif token == "5":
            style = style.copy(blink=True)
        elif token == "7":
            style = style.copy(reverse=True)
        elif token == "8":
            style = style.copy(conceal=True)
        elif token == "9":
            style = style.copy(strike=True)
        elif token == "22":
            style = style.copy(bold=False, dim=False)
        elif token == "23":
            style = style.copy(italic=False)
        elif token == "24":
            style = style.copy(underline=False)
        elif token == "25":
            style = style.copy(blink=False)
        elif token == "27":
            style = style.copy(reverse=False)
        elif token == "28":
            style = style.copy(conceal=False)
        elif token == "29":
            style = style.copy(strike=False)
        elif token.isdigit() and 30 <= int(token) <= 37:
            style = style.copy(fg=Color("indexed", int(token) - 30))
        elif token == "39":
            style = style.copy(fg=Color("default"))
        elif token.isdigit() and 40 <= int(token) <= 47:
            style = style.copy(bg=Color("indexed", int(token) - 40))
        elif token == "49":
            style = style.copy(bg=Color("default"))
        elif token.isdigit() and 90 <= int(token) <= 97:
            style = style.copy(fg=Color("indexed", int(token) - 90 + 8))
        elif token.isdigit() and 100 <= int(token) <= 107:
            style = style.copy(bg=Color("indexed", int(token) - 100 + 8))
        elif token in ("38", "48"):
            is_fg = token == "38"
            if i + 1 < len(tokens):
                mode = tokens[i + 1]
                if mode == "5" and i + 2 < len(tokens):
                    try:
                        val = int(tokens[i + 2])
                        if is_fg:
                            style = style.copy(fg=Color("indexed", val))
                        else:
                            style = style.copy(bg=Color("indexed", val))
                    except ValueError:
                        pass
                    i += 2
                elif mode == "2" and i + 4 < len(tokens):
                    try:
                        r = int(tokens[i + 2])
                        g = int(tokens[i + 3])
                        b = int(tokens[i + 4])
                        if is_fg:
                            style = style.copy(fg=Color("rgb", (r, g, b)))
                        else:
                            style = style.copy(bg=Color("rgb", (r, g, b)))
                    except ValueError:
                        pass
                    i += 4
        i += 1

    return style


def _style_to_ansi(style):
    """Convert a Style object to an ANSI escape sequence."""
    if style == Style():
        return ""

    params = []

    if style.bold is True:
        params.append("1")
    if style.dim is True:
        params.append("2")
    if style.italic is True:
        params.append("3")
    if style.underline is True:
        params.append("4")
    if style.blink is True:
        params.append("5")
    if style.reverse is True:
        params.append("7")
    if style.conceal is True:
        params.append("8")
    if style.strike is True:
        params.append("9")

    if style.fg is not None:
        if style.fg.mode == "indexed":
            if style.fg.value < 8:
                params.append(str(30 + style.fg.value))
            elif style.fg.value < 16:
                params.append(str(90 + style.fg.value - 8))
            else:
                params.append("38;5;%d" % style.fg.value)
        elif style.fg.mode == "rgb":
            r, g, b = style.fg.value
            params.append("38;2;%d;%d;%d" % (r, g, b))

    if style.bg is not None:
        if style.bg.mode == "indexed":
            if style.bg.value < 8:
                params.append(str(40 + style.bg.value))
            elif style.bg.value < 16:
                params.append(str(100 + style.bg.value - 8))
            else:
                params.append("48;5;%d" % style.bg.value)
        elif style.bg.mode == "rgb":
            r, g, b = style.bg.value
            params.append("48;2;%d;%d;%d" % (r, g, b))

    if not params:
        return ""

    return "\x1b[%sm" % ";".join(params)


def _merge_ansi_styles(base, new):
    """Merge two ANSI style sequences."""
    if new and ("\x1b[0m" in new or "\x1b[00m" in new or "\x1b[m" in new):
        return _style_to_ansi(_parse_sgr_sequence(new))

    base_style = _parse_sgr_sequence(base) if base else Style()
    new_style = _parse_sgr_sequence(new) if new else Style()
    merged = base_style.merge(new_style)
    return _style_to_ansi(merged)


def _get_background(ansi):
    """Extract just the background color as an ANSI sequence."""
    style = _parse_sgr_sequence(ansi)
    if style.bg is None or style.bg.mode == "default":
        return ""
    elif style.bg.mode == "indexed":
        if style.bg.value < 8:
            return "\x1b[%dm" % (40 + style.bg.value)
        elif style.bg.value < 16:
            return "\x1b[%dm" % (100 + style.bg.value - 8)
        else:
            return "\x1b[48;5;%dm" % style.bg.value
    elif style.bg.mode == "rgb":
        r, g, b = style.bg.value
        return "\x1b[48;2;%d;%d;%dm" % (r, g, b)
    return ""


# =============================================================================
# Terminal Buffer (from bittty/buffer.py)
# =============================================================================


class Buffer(object):
    """A 2D grid that stores terminal content."""

    def __init__(self, width, height):
        """Initialize buffer with given dimensions."""
        self.width = width
        self.height = height
        self._empty_style = Style()

        # Initialize grid with empty cells (Style, character)
        self.grid = []
        for _ in range(height):
            self.grid.append(self._create_empty_row())

    def _create_empty_row(self):
        """Create a row filled with empty cells."""
        return [(self._empty_style, " ") for _ in range(self.width)]

    def get_content(self):
        """Get buffer content as a 2D grid."""
        return [row[:] for row in self.grid]

    def get_cell(self, x, y):
        """Get cell at position."""
        if 0 <= y < self.height and 0 <= x < self.width:
            return self.grid[y][x]
        return (Style(), " ")

    def set_cell(self, x, y, char, style_or_ansi=None):
        """Set a single cell at position."""
        if 0 <= y < self.height and 0 <= x < self.width:
            if style_or_ansi is None:
                style = Style()
            elif isinstance(style_or_ansi, Style):
                style = style_or_ansi
            elif isinstance(style_or_ansi, str):
                style = _parse_sgr_sequence(style_or_ansi) if style_or_ansi else Style()
            else:
                style = Style()
            self.grid[y][x] = (style, char)

    def set(self, x, y, text, style_or_ansi=None):
        """Set text at position, overwriting existing content."""
        if not (0 <= y < self.height):
            return

        if style_or_ansi is None:
            style = Style()
        elif isinstance(style_or_ansi, Style):
            style = style_or_ansi
        elif isinstance(style_or_ansi, str):
            style = _parse_sgr_sequence(style_or_ansi) if style_or_ansi else Style()
        else:
            style = Style()

        for i, char in enumerate(text):
            if x + i >= self.width:
                break
            self.grid[y][x + i] = (style, char)

    def insert(self, x, y, text, style_or_ansi=None):
        """Insert text at position, shifting existing content right."""
        if not (0 <= y < self.height) or x >= self.width:
            return

        if style_or_ansi is None:
            style = Style()
        elif isinstance(style_or_ansi, Style):
            style = style_or_ansi
        elif isinstance(style_or_ansi, str):
            style = _parse_sgr_sequence(style_or_ansi) if style_or_ansi else Style()
        else:
            style = Style()

        row = self.grid[y]
        new_cells = [(style, char) for char in text]

        if x < len(row):
            new_row = row[:x] + new_cells + row[x:]
            self.grid[y] = new_row[: self.width]
        else:
            padding_needed = x - len(row)
            if padding_needed > 0:
                row.extend([(Style(), " ")] * padding_needed)
            row.extend(new_cells)
            self.grid[y] = row[: self.width]

    def delete(self, x, y, count=1):
        """Delete characters at position."""
        if not (0 <= y < self.height) or x >= self.width:
            return

        row = self.grid[y]
        if x < len(row):
            end_pos = min(x + count, len(row))
            new_row = row[:x] + row[end_pos:]
            while len(new_row) < self.width:
                new_row.append((Style(), " "))
            self.grid[y] = new_row

    def clear_region(self, x1, y1, x2, y2, style_or_ansi=None):
        """Clear a rectangular region."""
        if style_or_ansi is None:
            style = Style()
        elif isinstance(style_or_ansi, Style):
            style = style_or_ansi
        elif isinstance(style_or_ansi, str):
            style = _parse_sgr_sequence(style_or_ansi) if style_or_ansi else Style()
        else:
            style = Style()

        for y in range(max(0, y1), min(self.height, y2 + 1)):
            for x in range(max(0, x1), min(self.width, x2 + 1)):
                self.grid[y][x] = (style, " ")

    def clear_line(
        self, y, mode=ERASE_FROM_CURSOR_TO_END, cursor_x=0, style_or_ansi=None
    ):
        """Clear line content."""
        if not (0 <= y < self.height):
            return

        if style_or_ansi is None:
            style = Style()
        elif isinstance(style_or_ansi, Style):
            style = style_or_ansi
        elif isinstance(style_or_ansi, str):
            style = _parse_sgr_sequence(style_or_ansi) if style_or_ansi else Style()
        else:
            style = Style()

        if mode == ERASE_FROM_CURSOR_TO_END:
            for x in range(cursor_x, self.width):
                self.grid[y][x] = (style, " ")
        elif mode == ERASE_FROM_START_TO_CURSOR:
            for x in range(0, min(cursor_x + 1, self.width)):
                self.grid[y][x] = (style, " ")
        elif mode == ERASE_ALL:
            if style is self._empty_style:
                self.grid[y] = self._create_empty_row()
            else:
                self.grid[y] = [(style, " ") for _ in range(self.width)]

    def scroll_up(self, count):
        """Scroll content up, removing top lines and adding blank lines at bottom."""
        count = min(count, len(self.grid))
        if count <= 0:
            return

        del self.grid[:count]
        empty_rows = [self._create_empty_row() for _ in range(count)]
        self.grid.extend(empty_rows)

    def scroll_down(self, count):
        """Scroll content down, removing bottom lines and adding blank lines at top."""
        count = min(count, len(self.grid))
        if count <= 0:
            return

        del self.grid[-count:]
        empty_rows = [self._create_empty_row() for _ in range(count)]
        self.grid[:0] = empty_rows

    def scroll_region_up(self, top, bottom, count):
        """Scroll a specific region up by count lines."""
        if count <= 0 or top > bottom or bottom >= self.height:
            return

        region_height = bottom - top + 1
        count = min(count, region_height)

        self.grid[top : bottom + 1 - count] = self.grid[top + count : bottom + 1]

        for i in range(bottom + 1 - count, bottom + 1):
            self.grid[i] = self._create_empty_row()

    def scroll_region_down(self, top, bottom, count):
        """Scroll a specific region down by count lines."""
        if count <= 0 or top > bottom or bottom >= self.height:
            return

        region_height = bottom - top + 1
        count = min(count, region_height)

        self.grid[top + count : bottom + 1] = self.grid[top : bottom + 1 - count]

        for i in range(top, top + count):
            self.grid[i] = self._create_empty_row()

    def resize(self, width, height):
        """Resize buffer to new dimensions."""
        if len(self.grid) < height:
            for _ in range(height - len(self.grid)):
                self.grid.append([(Style(), " ") for _ in range(width)])
        elif len(self.grid) > height:
            self.grid = self.grid[:height]

        for y in range(len(self.grid)):
            row = self.grid[y]
            if len(row) < width:
                row.extend([(Style(), " ")] * (width - len(row)))
            elif len(row) > width:
                self.grid[y] = row[:width]

        self.width = width
        self.height = height

    def get_line_text(self, y):
        """Get plain text content of a line."""
        if 0 <= y < self.height:
            return "".join(cell[1] for cell in self.grid[y])
        return ""

    def get_line(
        self,
        y,
        width=None,
        cursor_x=-1,
        cursor_y=-1,
        show_cursor=False,
        mouse_x=-1,
        mouse_y=-1,
        show_mouse=False,
    ):
        """Get full ANSI sequence for a line with cursor/mouse highlighting."""
        if not (0 <= y < self.height):
            return ""

        # Use buffer width if not specified
        if width is None:
            width = self.width

        parts = []
        row = self.grid[y]
        current_style = Style()  # Start with default style

        # Process each cell up to specified width
        for x in range(min(len(row), width)):
            cell_style, char = row[x]

            # Handle mouse cursor (convert to 0-based)
            if show_mouse and x == (mouse_x - 1) and y == (mouse_y - 1):
                char = "\u2196"  # ↖

            # Handle text cursor position
            if show_cursor and x == cursor_x and y == cursor_y:
                # For cursor, apply reverse video on top of cell style
                transition = current_style.diff(cell_style)
                parts.append(transition)
                parts.append(CURSOR_CODE)
                parts.append(char)
                parts.append("\033[27m")  # Turn off reverse video only
                current_style = cell_style
            else:
                # Normal cell - generate diff from current to cell style
                transition = current_style.diff(cell_style)
                parts.append(transition)
                parts.append(char)
                current_style = cell_style

        # Pad to width if needed
        current_width = min(len(row), width)
        if current_width < width:
            # Transition to default style for padding
            reset_transition = current_style.diff(Style())
            parts.append(reset_transition)
            parts.append(" " * (width - current_width))
            current_style = Style()

        # Always end with a reset to prevent bleeding to next line
        final_reset = current_style.diff(Style())
        parts.append(final_reset)

        return "".join(parts)


# Style constants for cursor display
CURSOR_CODE = "\033[7m"  # Reverse video for cursor
RESET_CODE = "\033[0m"  # Reset all formatting


# =============================================================================
# Terminal Emulator (from bittty/terminal.py + parser/)
# =============================================================================


class Terminal(object):
    """A terminal emulator that handles all terminal logic."""

    def __init__(self, width=80, height=24):
        """Initialize terminal."""
        self.width = width
        self.height = height

        # Terminal state
        self.title = "Terminal"
        self.icon_title = "Terminal"
        self.cursor_x = 0
        self.cursor_y = 0
        self.cursor_visible = True
        self.cursor_blinking = True

        # Mouse position
        self.mouse_x = 0
        self.mouse_y = 0
        self.show_mouse = False

        # Terminal modes
        self.auto_wrap = True
        self.insert_mode = False
        self.cursor_application_mode = False
        self.numeric_keypad = True
        self.local_echo = True
        self.reverse_screen = False
        self.linefeed_newline_mode = False
        self.origin_mode = False
        self.ansi_mode = True
        self.scroll_mode = False
        self.auto_repeat = True
        self.backarrow_key_sends_bs = False
        self.bracketed_paste = False
        self.mouse_mode = None
        self.sgr_mouse = False
        self.urxvt_mouse = False
        self.auto_resize_mode = False
        self.keyboard_usage_mode = False

        # Screen buffers
        self.primary_buffer = Buffer(width, height)
        self.alt_buffer = Buffer(width, height)
        self.current_buffer = self.primary_buffer
        self.in_alt_screen = False

        # Scroll region (top, bottom) - 0-indexed
        self.scroll_top = 0
        self.scroll_bottom = height - 1

        # Current ANSI code for next write
        self.current_ansi_code = ""

        # Last printed character (for REP command)
        self.last_printed_char = " "

        # Character set state
        self.g0_charset = "B"
        self.g1_charset = "B"
        self.g2_charset = "B"
        self.g3_charset = "B"
        self.current_charset = 0
        self.single_shift = None
        self._charset_array = ["B", "B", "B", "B"]
        self._charset_cache = {}

        # Saved cursor state
        self.saved_cursor_x = 0
        self.saved_cursor_y = 0
        self.saved_ansi_code = ""

        # Parser state
        self._parse_buffer = ""
        self._parse_pos = 0
        self._parse_mode = None
        self._seq_start = 0
        self._scan_from = 0

        # Response buffer (for terminal queries)
        self._response_buffer = ""

    def feed(self, data):
        """Process input data through the parser."""
        self._parse_buffer += data

        while True:
            if self._parse_mode is None:
                # GROUND state - scan for control sequences
                trail_start = None
                pos = self._parse_pos
                buf = self._parse_buffer

                while pos < len(buf):
                    ch = buf[pos]

                    # Check for ESC
                    if ch == "\x1b":
                        # Flush printables before ESC
                        if pos > self._parse_pos:
                            self.write_text(buf[self._parse_pos : pos])

                        # Check what follows ESC
                        if pos + 1 >= len(buf):
                            trail_start = pos
                            break

                        next_ch = buf[pos + 1]
                        if next_ch == "[":
                            self._parse_mode = "csi"
                            self._seq_start = pos
                            self._scan_from = pos + 2
                            self._parse_pos = pos
                            break
                        elif next_ch == "]":
                            self._parse_mode = "osc"
                            self._seq_start = pos
                            self._scan_from = pos + 2
                            self._parse_pos = pos
                            break
                        elif next_ch == "P":
                            self._parse_mode = "dcs"
                            self._seq_start = pos
                            self._scan_from = pos + 2
                            self._parse_pos = pos
                            break
                        elif next_ch in "()":
                            # Character set designation
                            if pos + 2 < len(buf):
                                self._handle_charset_escape(buf[pos : pos + 3])
                                pos += 3
                                self._parse_pos = pos
                                continue
                            else:
                                trail_start = pos
                                break
                        elif next_ch in "*+":
                            # G2/G3 character set
                            if pos + 2 < len(buf):
                                self._handle_charset_escape(buf[pos : pos + 3])
                                pos += 3
                                self._parse_pos = pos
                                continue
                            else:
                                trail_start = pos
                                break
                        else:
                            # Simple escape sequence
                            self._handle_escape(buf[pos : pos + 2])
                            pos += 2
                            self._parse_pos = pos
                            continue

                    # C0 controls
                    elif ch == BEL:
                        if pos > self._parse_pos:
                            self.write_text(buf[self._parse_pos : pos])
                        self.bell()
                        pos += 1
                        self._parse_pos = pos
                        continue
                    elif ch == BS:
                        if pos > self._parse_pos:
                            self.write_text(buf[self._parse_pos : pos])
                        self.backspace()
                        pos += 1
                        self._parse_pos = pos
                        continue
                    elif ch == HT:
                        if pos > self._parse_pos:
                            self.write_text(buf[self._parse_pos : pos])
                        next_tab = ((self.cursor_x // 8) + 1) * 8
                        self.cursor_x = min(next_tab, self.width - 1)
                        pos += 1
                        self._parse_pos = pos
                        continue
                    elif ch in (LF, VT, FF):
                        if pos > self._parse_pos:
                            self.write_text(buf[self._parse_pos : pos])
                        self.line_feed()
                        pos += 1
                        self._parse_pos = pos
                        continue
                    elif ch == CR:
                        if pos > self._parse_pos:
                            self.write_text(buf[self._parse_pos : pos])
                        self.cursor_x = 0
                        pos += 1
                        self._parse_pos = pos
                        continue
                    elif ch == SO:
                        if pos > self._parse_pos:
                            self.write_text(buf[self._parse_pos : pos])
                        self.current_charset = 1
                        pos += 1
                        self._parse_pos = pos
                        continue
                    elif ch == SI:
                        if pos > self._parse_pos:
                            self.write_text(buf[self._parse_pos : pos])
                        self.current_charset = 0
                        pos += 1
                        self._parse_pos = pos
                        continue
                    elif ord(ch) < 0x20 and ch not in "\t\n\r":
                        # Other C0 control - skip
                        if pos > self._parse_pos:
                            self.write_text(buf[self._parse_pos : pos])
                        pos += 1
                        self._parse_pos = pos
                        continue

                    # 8-bit C1 controls (0x80-0x9F)
                    elif ch == C1_CSI:
                        # CSI - Control Sequence Introducer (8-bit)
                        if pos > self._parse_pos:
                            self.write_text(buf[self._parse_pos : pos])
                        self._parse_mode = "csi"
                        self._seq_start = pos
                        self._scan_from = pos + 1
                        self._parse_pos = pos
                        break
                    elif ch == C1_OSC:
                        # OSC - Operating System Command (8-bit)
                        if pos > self._parse_pos:
                            self.write_text(buf[self._parse_pos : pos])
                        self._parse_mode = "osc"
                        self._seq_start = pos
                        self._scan_from = pos + 1
                        self._parse_pos = pos
                        break
                    elif ch == C1_DCS:
                        # DCS - Device Control String (8-bit)
                        if pos > self._parse_pos:
                            self.write_text(buf[self._parse_pos : pos])
                        self._parse_mode = "dcs"
                        self._seq_start = pos
                        self._scan_from = pos + 1
                        self._parse_pos = pos
                        break
                    elif ch == C1_SS2:
                        # SS2 - Single Shift 2 (8-bit)
                        if pos > self._parse_pos:
                            self.write_text(buf[self._parse_pos : pos])
                        self.single_shift = 2
                        pos += 1
                        self._parse_pos = pos
                        continue
                    elif ch == C1_SS3:
                        # SS3 - Single Shift 3 (8-bit)
                        if pos > self._parse_pos:
                            self.write_text(buf[self._parse_pos : pos])
                        self.single_shift = 3
                        pos += 1
                        self._parse_pos = pos
                        continue
                    elif ch == C1_IND:
                        # IND - Index (8-bit, same as ESC D)
                        if pos > self._parse_pos:
                            self.write_text(buf[self._parse_pos : pos])
                        self.line_feed()
                        pos += 1
                        self._parse_pos = pos
                        continue
                    elif ch == C1_NEL:
                        # NEL - Next Line (8-bit, same as ESC E)
                        if pos > self._parse_pos:
                            self.write_text(buf[self._parse_pos : pos])
                        self.cursor_x = 0
                        self.line_feed()
                        pos += 1
                        self._parse_pos = pos
                        continue
                    elif ch == C1_RI:
                        # RI - Reverse Index (8-bit, same as ESC M)
                        if pos > self._parse_pos:
                            self.write_text(buf[self._parse_pos : pos])
                        if self.cursor_y <= self.scroll_top:
                            self.scroll(-1)
                        else:
                            self.cursor_y -= 1
                        pos += 1
                        self._parse_pos = pos
                        continue
                    elif ch == C1_HTS:
                        # HTS - Horizontal Tab Set (8-bit, same as ESC H)
                        if pos > self._parse_pos:
                            self.write_text(buf[self._parse_pos : pos])
                        # Tab stop - ignore for now
                        pos += 1
                        self._parse_pos = pos
                        continue
                    elif "\x80" <= ch <= "\x9f":
                        # Other C1 controls - skip
                        if pos > self._parse_pos:
                            self.write_text(buf[self._parse_pos : pos])
                        pos += 1
                        self._parse_pos = pos
                        continue

                    pos += 1

                else:
                    # Reached end of buffer - flush remaining printables
                    if self._parse_pos < len(buf):
                        self.write_text(buf[self._parse_pos :])
                        self._parse_pos = len(buf)

                if trail_start is not None:
                    if self._parse_pos < trail_start:
                        self.write_text(buf[self._parse_pos : trail_start])
                        self._parse_pos = trail_start
                    break

                if self._parse_mode is None:
                    break

            if self._parse_mode == "csi":
                # Find CSI terminator
                buf = self._parse_buffer
                for i in range(self._scan_from, len(buf)):
                    ch = buf[i]
                    if "\x40" <= ch <= "\x7e":
                        # CSI final character
                        self._dispatch_csi(buf[self._seq_start : i + 1])
                        self._parse_pos = i + 1
                        self._parse_mode = None
                        break
                    elif ch in "\x18\x1a":
                        # CAN/SUB - abort
                        self._parse_pos = i + 1
                        self._parse_mode = None
                        break
                else:
                    break

            elif self._parse_mode in ("osc", "dcs"):
                # Find string terminator (ST or BEL)
                buf = self._parse_buffer
                # Determine content start based on 7-bit vs 8-bit introducer
                intro_char = buf[self._seq_start]
                if intro_char == ESC:
                    content_start = self._seq_start + 2  # ESC ] or ESC P
                else:
                    content_start = self._seq_start + 1  # 8-bit C1_OSC or C1_DCS
                for i in range(self._scan_from, len(buf)):
                    if buf[i] == BEL:
                        content = buf[content_start:i]
                        if self._parse_mode == "osc":
                            self._dispatch_osc(content)
                        self._parse_pos = i + 1
                        self._parse_mode = None
                        break
                    elif buf[i : i + 2] == "\x1b\\":
                        content = buf[content_start:i]
                        if self._parse_mode == "osc":
                            self._dispatch_osc(content)
                        self._parse_pos = i + 2
                        self._parse_mode = None
                        break
                    elif buf[i] == C1_ST:
                        # 8-bit ST terminator
                        content = buf[content_start:i]
                        if self._parse_mode == "osc":
                            self._dispatch_osc(content)
                        self._parse_pos = i + 1
                        self._parse_mode = None
                        break
                    elif buf[i] in "\x18\x1a":
                        self._parse_pos = i + 1
                        self._parse_mode = None
                        break
                else:
                    break

        # Compact processed buffer
        if self._parse_pos > 0:
            delta = self._parse_pos
            self._parse_buffer = self._parse_buffer[self._parse_pos :]
            self._parse_pos = 0
            if self._parse_mode is not None and delta:
                self._seq_start = max(0, self._seq_start - delta)
                self._scan_from = max(0, self._scan_from - delta)

    def _handle_escape(self, data):
        """Handle simple escape sequences."""
        if len(data) < 2:
            return

        ch = data[1]
        if ch == "c":
            self._reset_terminal()
        elif ch == "D":
            self.line_feed()
        elif ch == "M":
            if self.cursor_y <= self.scroll_top:
                self.scroll(-1)
            else:
                self.cursor_y -= 1
        elif ch == "7":
            self.save_cursor()
        elif ch == "8":
            self.restore_cursor()
        elif ch == "=":
            self.numeric_keypad = False
        elif ch == ">":
            self.numeric_keypad = True
        elif ch == "E":
            self.cursor_x = 0
            self.line_feed()
        elif ch == "H":
            pass  # Tab stop - ignore for now
        elif ch == "N":
            self.single_shift = 2
        elif ch == "O":
            self.single_shift = 3

    def _handle_charset_escape(self, data):
        """Handle charset designation sequences."""
        if len(data) < 3:
            return

        designator = data[1]
        charset = data[2]

        if designator == "(":
            self.g0_charset = charset
            self._charset_array[0] = charset
        elif designator == ")":
            self.g1_charset = charset
            self._charset_array[1] = charset
        elif designator == "*":
            self.g2_charset = charset
            self._charset_array[2] = charset
        elif designator == "+":
            self.g3_charset = charset
            self._charset_array[3] = charset

    def _dispatch_csi(self, data):
        """Dispatch CSI escape sequence."""
        # Handle both 7-bit (ESC[) and 8-bit (C1_CSI) sequences
        if data.startswith("\x1b["):
            # 7-bit: ESC [ params final
            if len(data) < 3:
                return
            content_start = 2
        elif data.startswith(C1_CSI):
            # 8-bit: C1_CSI params final
            if len(data) < 2:
                return
            content_start = 1
        else:
            return

        final_char = data[-1]

        # SGR - pass to style system
        if final_char == "m":
            if ">" in data:
                return
            self.current_ansi_code = _merge_ansi_styles(self.current_ansi_code, data)
            return

        # Parse parameters
        params, intermediates, final_char = self._parse_csi_params(data, content_start)

        if final_char in ("H", "f"):
            row = (params[0] if params and params[0] is not None else 1) - 1
            col = (params[1] if len(params) > 1 and params[1] is not None else 1) - 1
            self.set_cursor(col, row)
        elif final_char == "A":
            count = params[0] if params and params[0] is not None else 1
            self.cursor_y = max(0, self.cursor_y - count)
        elif final_char == "B":
            count = params[0] if params and params[0] is not None else 1
            self.cursor_y = min(self.height - 1, self.cursor_y + count)
        elif final_char == "C":
            count = params[0] if params and params[0] is not None else 1
            self.cursor_x = min(self.width - 1, self.cursor_x + count)
        elif final_char == "D":
            count = params[0] if params and params[0] is not None else 1
            self.cursor_x = max(0, self.cursor_x - count)
        elif final_char == "G":
            col = (params[0] if params and params[0] is not None else 1) - 1
            self.set_cursor(col, None)
        elif final_char == "d":
            row = (params[0] if params and params[0] is not None else 1) - 1
            self.set_cursor(None, row)
        elif final_char == "J":
            mode = params[0] if params and params[0] is not None else 0
            self.clear_screen(mode)
        elif final_char == "K":
            mode = params[0] if params and params[0] is not None else 0
            self.clear_line(mode)
        elif final_char == "L":
            count = params[0] if params and params[0] is not None else 1
            self.insert_lines(count)
        elif final_char == "M":
            count = params[0] if params and params[0] is not None else 1
            self.delete_lines(count)
        elif final_char == "@":
            count = params[0] if params and params[0] is not None else 1
            self.insert_characters(count)
        elif final_char == "P":
            count = params[0] if params and params[0] is not None else 1
            self.delete_characters(count)
        elif final_char == "X":
            count = params[0] if params and params[0] is not None else 1
            for _ in range(count):
                self.current_buffer.set(
                    self.cursor_x, self.cursor_y, " ", self.current_ansi_code
                )
                if self.cursor_x < self.width - 1:
                    self.cursor_x += 1
        elif final_char == "S":
            count = params[0] if params and params[0] is not None else 1
            self.scroll(count)
        elif final_char == "T":
            count = params[0] if params and params[0] is not None else 1
            self.scroll(-count)
        elif final_char == "r":
            top = (params[0] if params and params[0] is not None else 1) - 1
            bottom = (
                params[1] if len(params) > 1 and params[1] is not None else self.height
            ) - 1
            self.set_scroll_region(top, bottom)
        elif final_char == "s":
            self.save_cursor()
        elif final_char == "u":
            self.restore_cursor()
        elif final_char == "b":
            count = params[0] if params and params[0] is not None else 1
            self.repeat_last_character(count)
        elif final_char == "n":
            param = params[0] if params and params[0] is not None else 0
            if param == 6:
                row = self.cursor_y + 1
                col = self.cursor_x + 1
                self.respond("\033[%d;%dR" % (row, col))
            elif param == 5:
                self.respond("\033[0n")
        elif final_char == "c":
            if not intermediates:
                param = params[0] if params and params[0] is not None else 0
                if param == 0:
                    self.respond("\033[?62;1;6;8;9;15;18;21;22;23c")
            elif ">" in intermediates:
                self.respond("\033[>1;10;0c")
        elif final_char == "h":
            if "?" in intermediates:
                self._dispatch_private_mode(params, True)
            else:
                self._dispatch_mode(params, True)
        elif final_char == "l":
            if "?" in intermediates:
                self._dispatch_private_mode(params, False)
            else:
                self._dispatch_mode(params, False)
        elif final_char == "p" and "$" in intermediates:
            # DECRQM - Request Mode Status
            mode = params[0] if params and params[0] is not None else 0
            is_private = "?" in intermediates
            if is_private:
                status = self._get_private_mode_status(mode)
            else:
                status = self._get_ansi_mode_status(mode)
            prefix = "?" if is_private else ""
            self.respond("\033[%s%d;%d$y" % (prefix, mode, status))
        elif final_char == "y" and "$" in intermediates:
            # DECRPM - Mode status report (response) - ignore
            pass

    def _parse_csi_params(self, data, content_start=2):
        """Parse CSI parameters."""
        if len(data) < content_start + 1:
            return [], [], ""

        content = data[content_start:]
        if not content:
            return [], [], ""

        final_char = content[-1]
        sequence = content[:-1]

        if not sequence:
            return [], [], final_char

        private_markers = []
        param_start = 0
        for i, char in enumerate(sequence):
            if char in "?<=>":
                private_markers.append(char)
                param_start = i + 1
            else:
                break

        intermediates = []
        param_end = len(sequence)
        for i in range(len(sequence) - 1, -1, -1):
            char = sequence[i]
            if 0x20 <= ord(char) <= 0x2F:
                intermediates.insert(0, char)
                param_end = i
            else:
                break

        params = []
        param_part = sequence[param_start:param_end]
        if param_part:
            for part in param_part.split(";"):
                if not part:
                    params.append(None)
                else:
                    main_part = part.split(":")[0]
                    try:
                        params.append(int(main_part))
                    except ValueError:
                        params.append(main_part)

        return params, private_markers + intermediates, final_char

    def _dispatch_mode(self, params, set_mode):
        """Handle SM/RM for standard modes."""
        for param in params:
            if param is None:
                continue
            if param == 4:
                self.insert_mode = set_mode
            elif param == 7:
                self.auto_wrap = set_mode
            elif param == 12:
                self.local_echo = not set_mode
            elif param == 20:
                self.linefeed_newline_mode = set_mode
            elif param == 25:
                self.cursor_visible = set_mode

    def _dispatch_private_mode(self, params, set_mode):
        """Handle SM/RM for private modes."""
        for param in params:
            if param is None:
                continue
            if param == 1:
                self.cursor_application_mode = set_mode
            elif param == 2:
                self.ansi_mode = set_mode
            elif param == 3:
                if set_mode:
                    self.resize(132, self.height)
                else:
                    self.resize(80, self.height)
            elif param == 5:
                self.reverse_screen = set_mode
            elif param == 6:
                self.origin_mode = set_mode
            elif param == 7:
                self.auto_wrap = set_mode
            elif param == 12:
                self.cursor_blinking = set_mode
            elif param == 25:
                self.cursor_visible = set_mode
            elif param == 47:
                if set_mode:
                    self.alternate_screen_on()
                else:
                    self.alternate_screen_off()
            elif param == 66:
                self.numeric_keypad = not set_mode
            elif param == 67:
                self.backarrow_key_sends_bs = set_mode
            elif param == 1000:
                self.mouse_mode = "vt200" if set_mode else None
            elif param == 1002:
                self.mouse_mode = "button" if set_mode else None
            elif param == 1003:
                self.mouse_mode = "any" if set_mode else None
            elif param == 1006:
                self.sgr_mouse = set_mode
            elif param == 1047:
                if set_mode:
                    self.alternate_screen_on()
                else:
                    self.alternate_screen_off()
            elif param == 1048:
                if set_mode:
                    self.save_cursor()
                else:
                    self.restore_cursor()
            elif param == 1049:
                if set_mode:
                    self.save_cursor()
                    self.alternate_screen_on()
                else:
                    self.alternate_screen_off()
                    self.restore_cursor()
            elif param == 2004:
                self.bracketed_paste = set_mode

    def _get_private_mode_status(self, mode):
        """Get the status of a private mode for DECRQM response.

        Status codes:
        0 = not recognized
        1 = set
        2 = reset
        3 = permanently set
        4 = permanently reset
        """
        if mode == 1:  # DECCKM
            return 1 if self.cursor_application_mode else 2
        elif mode == 2:  # DECANM
            return 1 if self.ansi_mode else 2
        elif mode == 3:  # DECCOLM
            return 1 if self.width == 132 else 2
        elif mode == 6:  # DECOM
            return 1 if self.origin_mode else 2
        elif mode == 7:  # DECAWM
            return 1 if self.auto_wrap else 2
        elif mode == 12:  # Cursor blinking
            return 1 if self.cursor_blinking else 2
        elif mode == 25:  # DECTCEM
            return 1 if self.cursor_visible else 2
        elif mode == 47 or mode == 1047:  # Alternate screen
            return 1 if self.in_alt_screen else 2
        elif mode == 1049:  # Alternate screen + cursor
            return 1 if self.in_alt_screen else 2
        elif mode == 1000:  # VT200 mouse
            return 1 if self.mouse_mode == "vt200" else 2
        elif mode == 1002:  # Button event mouse
            return 1 if self.mouse_mode == "button" else 2
        elif mode == 1003:  # Any event mouse
            return 1 if self.mouse_mode == "any" else 2
        elif mode == 1006:  # SGR mouse
            return 1 if self.sgr_mouse else 2
        elif mode == 2004:  # Bracketed paste
            return 1 if self.bracketed_paste else 2
        else:
            return 0  # Not recognized

    def _get_ansi_mode_status(self, mode):
        """Get the status of an ANSI mode for DECRQM response."""
        if mode == 4:  # IRM
            return 1 if self.insert_mode else 2
        elif mode == 7:  # AWM
            return 1 if self.auto_wrap else 2
        elif mode == 12:  # SRM
            # SRM works backwards: mode set = echo disabled
            return 1 if not self.local_echo else 2
        elif mode == 20:  # LNM
            return 1 if self.linefeed_newline_mode else 2
        elif mode == 25:  # DECTCEM
            return 1 if self.cursor_visible else 2
        else:
            return 0  # Not recognized

    def _dispatch_osc(self, content):
        """Dispatch OSC sequence."""
        if not content:
            return

        parts = content.split(";", 1)
        if not parts:
            return

        try:
            cmd = int(parts[0])
            data = parts[1] if len(parts) >= 2 else ""
        except ValueError:
            return

        if cmd == 0:
            self.set_title(data)
            self.set_icon_title(data)
        elif cmd == 1:
            self.set_icon_title(data)
        elif cmd == 2:
            self.set_title(data)
        elif cmd == 10:
            if data == "?":
                self.respond("\033]10;rgb:ffff/ffff/ffff\007")
        elif cmd == 11:
            if data == "?":
                self.respond("\033]11;rgb:0000/0000/0000\007")

    def _reset_terminal(self):
        """Reset terminal to initial state."""
        self.clear_screen(ERASE_ALL)
        self.set_cursor(0, 0)
        self.current_ansi_code = ""
        self.g0_charset = "B"
        self.g1_charset = "B"
        self.g2_charset = "B"
        self.g3_charset = "B"
        self.current_charset = 0
        self.single_shift = None
        self._charset_array = ["B", "B", "B", "B"]

    def write_text(self, text):
        """Write text at cursor position."""
        if self.cursor_x >= self.width:
            if self.auto_wrap:
                self.line_feed()
                self.cursor_x = 0
            else:
                self.cursor_x = self.width - 1

        translated_text = self._translate_charset(text)

        if self.insert_mode:
            self.current_buffer.insert(
                self.cursor_x, self.cursor_y, translated_text, self.current_ansi_code
            )
        else:
            self.current_buffer.set(
                self.cursor_x, self.cursor_y, translated_text, self.current_ansi_code
            )

        if self.auto_wrap or self.cursor_x < self.width - 1:
            self.cursor_x += len(translated_text)

        if translated_text:
            self.last_printed_char = translated_text[-1]

    def _translate_charset(self, text):
        """Character set translation."""
        if self.single_shift is not None:
            if not text:
                return text

            first_char = text[0]
            remaining = text[1:] if len(text) > 1 else ""

            charset_designator = self._charset_array[self.single_shift]
            self.single_shift = None

            if charset_designator in self._charset_cache:
                charset_map = self._charset_cache[charset_designator]
            else:
                charset_map = _get_charset(charset_designator)
                self._charset_cache[charset_designator] = charset_map

            translated_first = charset_map.get(first_char, first_char)

            if remaining:
                return translated_first + self._translate_charset(remaining)
            else:
                return translated_first

        current_charset_designator = self._charset_array[self.current_charset]
        if current_charset_designator == "B":
            return text

        if not text:
            return text

        if current_charset_designator in self._charset_cache:
            charset_map = self._charset_cache[current_charset_designator]
        else:
            charset_map = _get_charset(current_charset_designator)
            self._charset_cache[current_charset_designator] = charset_map

        if not charset_map:
            return text

        result = [charset_map.get(char, char) for char in text]
        return "".join(result)

    def line_feed(self):
        """Perform line feed."""
        if self.cursor_y == self.scroll_bottom:
            self.scroll(1)
        elif self.cursor_y < self.scroll_bottom:
            self.cursor_y += 1

        if self.linefeed_newline_mode:
            self.cursor_x = 0

    def backspace(self):
        """Move cursor back one position."""
        if self.cursor_x > 0:
            self.cursor_x -= 1
        elif self.cursor_y > 0:
            self.cursor_y -= 1
            self.cursor_x = self.width - 1

    def bell(self):
        """Terminal bell."""
        pass

    def set_cursor(self, x, y):
        """Set cursor position."""
        if x is not None:
            self.cursor_x = max(0, min(x, self.width - 1))
        if y is not None:
            self.cursor_y = max(0, min(y, self.height - 1))

    def save_cursor(self):
        """Save cursor position and attributes."""
        self.saved_cursor_x = self.cursor_x
        self.saved_cursor_y = self.cursor_y
        self.saved_ansi_code = self.current_ansi_code

    def restore_cursor(self):
        """Restore cursor position and attributes."""
        self.cursor_x = self.saved_cursor_x
        self.cursor_y = self.saved_cursor_y
        self.current_ansi_code = self.saved_ansi_code

    def clear_screen(self, mode=ERASE_FROM_CURSOR_TO_END):
        """Clear screen."""
        bg_ansi = _get_background(self.current_ansi_code)

        if mode == ERASE_FROM_CURSOR_TO_END:
            self.current_buffer.clear_line(
                self.cursor_y, ERASE_FROM_CURSOR_TO_END, self.cursor_x, bg_ansi
            )
            for y in range(self.cursor_y + 1, self.height):
                self.current_buffer.clear_line(y, ERASE_ALL, 0, bg_ansi)
        elif mode == ERASE_FROM_START_TO_CURSOR:
            for y in range(self.cursor_y):
                self.current_buffer.clear_line(y, ERASE_ALL, 0, bg_ansi)
            self.clear_line(ERASE_FROM_START_TO_CURSOR)
        elif mode == ERASE_ALL:
            for y in range(self.height):
                self.current_buffer.clear_line(y, ERASE_ALL, 0, bg_ansi)
            self.cursor_x = 0
            self.cursor_y = 0

    def clear_line(self, mode=ERASE_FROM_CURSOR_TO_END):
        """Clear line."""
        bg_ansi = _get_background(self.current_ansi_code)
        self.current_buffer.clear_line(self.cursor_y, mode, self.cursor_x, bg_ansi)

    def set_scroll_region(self, top, bottom):
        """Set scroll region."""
        self.scroll_top = max(0, min(top, self.height - 1))
        self.scroll_bottom = max(self.scroll_top, min(bottom, self.height - 1))

    def scroll(self, lines):
        """Scroll content."""
        if lines == 0 or self.scroll_top > self.scroll_bottom:
            return

        abs_lines = abs(lines)

        if lines > 0:
            self.current_buffer.scroll_region_up(
                self.scroll_top, self.scroll_bottom, abs_lines
            )
        else:
            self.current_buffer.scroll_region_down(
                self.scroll_top, self.scroll_bottom, abs_lines
            )

    def insert_lines(self, count):
        """Insert blank lines at cursor position."""
        for _ in range(count):
            for y in range(self.height - 1, self.cursor_y, -1):
                if y - 1 >= 0:
                    for x in range(self.width):
                        cell = self.current_buffer.get_cell(x, y - 1)
                        self.current_buffer.set_cell(x, y, cell[1], cell[0])
            self.current_buffer.clear_line(self.cursor_y, ERASE_ALL)

    def delete_lines(self, count):
        """Delete lines at cursor position."""
        for _ in range(count):
            for y in range(self.cursor_y, self.height - 1):
                if y + 1 < self.height:
                    for x in range(self.width):
                        cell = self.current_buffer.get_cell(x, y + 1)
                        self.current_buffer.set_cell(x, y, cell[1], cell[0])
            self.current_buffer.clear_line(self.height - 1, ERASE_ALL)

    def insert_characters(self, count):
        """Insert blank characters at cursor position."""
        if not (0 <= self.cursor_y < self.height):
            return
        spaces = " " * count
        self.current_buffer.insert(
            self.cursor_x, self.cursor_y, spaces, self.current_ansi_code
        )

    def delete_characters(self, count):
        """Delete characters at cursor position."""
        if not (0 <= self.cursor_y < self.height):
            return
        self.current_buffer.delete(self.cursor_x, self.cursor_y, count)

    def repeat_last_character(self, count):
        """Repeat the last printed character."""
        if count > 0 and self.last_printed_char:
            repeated_text = self.last_printed_char * count
            self.write_text(repeated_text)

    def alternate_screen_on(self):
        """Switch to alternate screen."""
        if not self.in_alt_screen:
            self.current_buffer = self.alt_buffer
            self.in_alt_screen = True

    def alternate_screen_off(self):
        """Switch to primary screen."""
        if self.in_alt_screen:
            self.current_buffer = self.primary_buffer
            self.in_alt_screen = False

    def set_title(self, title):
        """Set terminal title."""
        self.title = title

    def set_icon_title(self, icon_title):
        """Set terminal icon title."""
        self.icon_title = icon_title

    def respond(self, data):
        """Send response (stored for later retrieval)."""
        self._response_buffer += data

    def get_response(self):
        """Get and clear response buffer."""
        response = self._response_buffer
        self._response_buffer = ""
        return response

    def resize(self, width, height):
        """Resize terminal."""
        self.width = width
        self.height = height
        self.primary_buffer.resize(width, height)
        self.alt_buffer.resize(width, height)
        self.scroll_bottom = height - 1
        self.cursor_x = min(self.cursor_x, width - 1)
        self.cursor_y = min(self.cursor_y, height - 1)

    def get_plain_text(self):
        """Get buffer content as plain text."""
        lines = []
        for y in range(self.height):
            line = self.current_buffer.get_line_text(y).rstrip()
            lines.append(line)
        while lines and not lines[-1]:
            lines.pop()
        return "\n".join(lines)


# =============================================================================
# Cocoa Terminal
# =============================================================================


class CocoaTerminal:
    """Native macOS terminal using Cocoa via ctypes."""

    # Standard 16-color palette
    COLORS = [
        (0, 0, 0),  # Black
        (194, 54, 33),  # Red
        (37, 188, 36),  # Green
        (173, 173, 39),  # Yellow
        (73, 46, 225),  # Blue
        (211, 56, 211),  # Magenta
        (51, 187, 200),  # Cyan
        (203, 204, 205),  # White
        (129, 131, 131),  # Bright Black
        (252, 57, 31),  # Bright Red
        (49, 231, 34),  # Bright Green
        (234, 236, 35),  # Bright Yellow
        (88, 51, 255),  # Bright Blue
        (249, 53, 248),  # Bright Magenta
        (20, 240, 240),  # Bright Cyan
        (233, 235, 235),  # Bright White
    ]

    def __init__(self, executable, argv, title="Terminal"):
        self.executable = executable
        self.argv = argv
        self.title = title

        self.app = None
        self.window = None
        self.text_view = None
        self.scroll_view = None

        self.master_fd = None
        self.slave_fd = None
        self.process = None

        self.terminal = Terminal(80, 24)
        self.running = True

        self._char_width = 8.0
        self._char_height = 14.0

    def _setup_app(self):
        """Initialize NSApplication."""
        NSApplication = _get_class(b"NSApplication")
        self.app = _send_message(NSApplication, b"sharedApplication")
        _send_message(
            self.app,
            b"setActivationPolicy:",
            NSApplicationActivationPolicyRegular,
            argtypes=[c_long],
        )

    def _setup_window(self):
        """Create the terminal window."""
        NSWindow = _get_class(b"NSWindow")
        NSScrollView = _get_class(b"NSScrollView")
        NSTextView = _get_class(b"NSTextView")
        NSColor = _get_class(b"NSColor")
        NSFont = _get_class(b"NSFont")

        # Calculate window size based on terminal dimensions
        width = self.terminal.width * self._char_width + 20
        height = self.terminal.height * self._char_height + 20

        # Create window
        rect = NSRect.make(100, 100, width, height)
        self.window = _send_message(NSWindow, b"alloc")
        self.window = _send_message(
            self.window,
            b"initWithContentRect:styleMask:backing:defer:",
            rect,
            NSWindowStyleMaskDefault,
            NSBackingStoreBuffered,
            False,
            argtypes=[NSRect, c_uint, c_uint, c_bool],
        )

        # Set title
        _send_message(
            self.window, b"setTitle:", _create_nsstring(self.title), argtypes=[c_void_p]
        )

        # Create scroll view
        content_rect = NSRect.make(0, 0, width, height)
        self.scroll_view = _send_message(NSScrollView, b"alloc")
        self.scroll_view = _send_message(
            self.scroll_view, b"initWithFrame:", content_rect, argtypes=[NSRect]
        )
        _send_message(
            self.scroll_view, b"setHasVerticalScroller:", True, argtypes=[c_bool]
        )
        _send_message(
            self.scroll_view, b"setHasHorizontalScroller:", False, argtypes=[c_bool]
        )

        # Create text view
        text_rect = NSRect.make(0, 0, width - 20, height - 20)
        self.text_view = _send_message(NSTextView, b"alloc")
        self.text_view = _send_message(
            self.text_view, b"initWithFrame:", text_rect, argtypes=[NSRect]
        )

        # Configure text view
        _send_message(self.text_view, b"setEditable:", False, argtypes=[c_bool])
        _send_message(self.text_view, b"setSelectable:", True, argtypes=[c_bool])

        # Set monospace font
        font = _send_message(
            NSFont,
            b"fontWithName:size:",
            _create_nsstring("Menlo"),
            12.0,
            argtypes=[c_void_p, c_double],
        )
        if not font:
            font = _send_message(
                NSFont, b"userFixedPitchFontOfSize:", 12.0, argtypes=[c_double]
            )
        _send_message(self.text_view, b"setFont:", font, argtypes=[c_void_p])

        # Set colors
        bg_color = _send_message(
            NSColor,
            b"colorWithCalibratedRed:green:blue:alpha:",
            0.0,
            0.0,
            0.0,
            1.0,
            argtypes=[c_double, c_double, c_double, c_double],
        )
        fg_color = _send_message(
            NSColor,
            b"colorWithCalibratedRed:green:blue:alpha:",
            0.9,
            0.9,
            0.9,
            1.0,
            argtypes=[c_double, c_double, c_double, c_double],
        )
        _send_message(
            self.text_view, b"setBackgroundColor:", bg_color, argtypes=[c_void_p]
        )
        _send_message(self.text_view, b"setTextColor:", fg_color, argtypes=[c_void_p])

        # Add text view to scroll view
        _send_message(
            self.scroll_view, b"setDocumentView:", self.text_view, argtypes=[c_void_p]
        )

        # Add scroll view to window
        _send_message(
            self.window, b"setContentView:", self.scroll_view, argtypes=[c_void_p]
        )

        # Show window
        _send_message(self.window, b"makeKeyAndOrderFront:", None, argtypes=[c_void_p])

        # Activate app
        _send_message(self.app, b"activateIgnoringOtherApps:", True, argtypes=[c_bool])

    def _setup_pty(self):
        """Create PTY and spawn subprocess."""
        self.master_fd, self.slave_fd = pty.openpty()

        # Set non-blocking on master
        flags = fcntl.fcntl(self.master_fd, fcntl.F_GETFL)
        fcntl.fcntl(self.master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        # Set initial terminal size
        self._set_pty_size(self.terminal.width, self.terminal.height)

        # Prepare environment
        env = os.environ.copy()
        env["NUITKA_EMBEDDED_TERMINAL"] = "1"
        env["TERM"] = "xterm-256color"
        env["COLORTERM"] = "truecolor"

        # Spawn subprocess
        self.process = subprocess.Popen(
            [self.executable] + self.argv[1:],
            stdin=self.slave_fd,
            stdout=self.slave_fd,
            stderr=self.slave_fd,
            env=env,
            start_new_session=True,
        )

        # Close slave in parent
        os.close(self.slave_fd)
        self.slave_fd = None

    def _set_pty_size(self, cols, rows):
        """Set PTY window size."""
        if self.master_fd is not None:
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)

    def _update_display(self):
        """Update the text view with terminal buffer content."""
        NSString = _get_class(b"NSString")

        text = self.terminal.get_plain_text()
        ns_text = _send_message(NSString, b"alloc")
        ns_text = _send_message(
            ns_text,
            b"initWithUTF8String:",
            text.encode("utf8"),
            argtypes=[c_char_p],
        )

        _send_message(self.text_view, b"setString:", ns_text, argtypes=[c_void_p])

        # Scroll to bottom
        _send_message(
            self.text_view,
            b"scrollRangeToVisible:",
            NSRange(len(text), 0),
            argtypes=[NSRange],
        )

    def _read_pty(self):
        """Read from PTY and process data."""
        if self.master_fd is None:
            return

        try:
            data = os.read(self.master_fd, 4096)
            if data:
                self.terminal.feed(data.decode("utf-8", errors="replace"))
                self._update_display()
        except BlockingIOError:
            pass
        except OSError:
            self.running = False

    def _handle_key_event(self, event):
        """Handle a key event."""
        if self.master_fd is None:
            return

        # Get key code and characters
        key_code = _send_message(event, b"keyCode", restype=c_uint)
        chars = _send_message(event, b"characters")
        char_str = _get_nsstring_value(chars) if chars else ""

        # Special key mappings
        key_map = {
            0x7B: b"\x1b[D",  # Left
            0x7C: b"\x1b[C",  # Right
            0x7E: b"\x1b[A",  # Up
            0x7D: b"\x1b[B",  # Down
            0x24: b"\r",  # Return
            0x33: b"\x7f",  # Backspace
            0x30: b"\t",  # Tab
            0x35: b"\x1b",  # Escape
            0x73: b"\x1b[H",  # Home
            0x77: b"\x1b[F",  # End
            0x74: b"\x1b[5~",  # Page Up
            0x79: b"\x1b[6~",  # Page Down
            0x75: b"\x1b[3~",  # Delete
        }

        if key_code in key_map:
            data = key_map[key_code]
        elif char_str:
            data = char_str.encode("utf8")
        else:
            return

        try:
            os.write(self.master_fd, data)
        except OSError:
            pass

    def _run_event_loop(self):
        """Run the Cocoa event loop."""
        NSRunLoop = _get_class(b"NSRunLoop")
        NSDate = _get_class(b"NSDate")
        NSEvent = _get_class(b"NSEvent")
        NSApplication = _get_class(b"NSApplication")

        run_loop = _send_message(NSRunLoop, b"currentRunLoop")

        # Get default run loop mode
        NSDefaultRunLoopMode = _send_message(
            _send_message(NSString := _get_class(b"NSString"), b"alloc"),
            b"initWithUTF8String:",
            b"kCFRunLoopDefaultMode",
            argtypes=[c_char_p],
        )

        while self.running:
            # Check if process exited
            if self.process and self.process.poll() is not None:
                # Read any remaining output
                self._read_pty()
                self._update_display()
                self.running = False
                break

            # Process events with timeout
            date = _send_message(
                NSDate,
                b"dateWithTimeIntervalSinceNow:",
                0.05,
                argtypes=[c_double],
            )

            # Get next event
            event = _send_message(
                self.app,
                b"nextEventMatchingMask:untilDate:inMode:dequeue:",
                c_ulong(0xFFFFFFFF),  # NSEventMaskAny
                date,
                NSDefaultRunLoopMode,
                True,
                argtypes=[c_ulong, c_void_p, c_void_p, c_bool],
            )

            if event:
                event_type = _send_message(event, b"type", restype=c_ulong)

                # Handle key events (keyDown = 10)
                if event_type == 10:
                    self._handle_key_event(event)
                else:
                    _send_message(self.app, b"sendEvent:", event, argtypes=[c_void_p])

                _send_message(self.app, b"updateWindows")

            # Read from PTY
            self._read_pty()

    def run(self):
        """Run the terminal."""
        try:
            self._setup_app()
            self._setup_window()
            self._setup_pty()
            self._run_event_loop()
        finally:
            self._cleanup()

    def _cleanup(self):
        """Clean up resources."""
        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except OSError:
                pass

        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.process.kill()


# =============================================================================
# Entry Point
# =============================================================================


def launch_embedded_terminal(executable, argv):
    """Launch the embedded terminal with the given executable.

    This is the main entry point called by the Nuitka plugin when
    the app detects it's running without a TTY on macOS.

    Args:
        executable: Path to the executable to run
        argv: Command line arguments (including argv[0])
    """
    terminal = CocoaTerminal(executable, argv)
    terminal.run()


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
