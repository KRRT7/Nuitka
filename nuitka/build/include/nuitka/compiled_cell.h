//     Copyright 2026, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file

#pragma once
#ifndef __NUITKA_COMPILED_CELL_H__
#define __NUITKA_COMPILED_CELL_H__

/* This is a clone of the normal PyCell structure. We should keep it binary
 * compatible, just in case somebody crazy insists on it.
 */

/* This file is included from another C file, help IDEs to still parse it on its own. */
#ifdef __IDE_ONLY__
#include "nuitka/prelude.h"
#endif

extern PyTypeObject Nuitka_Cell_Type;

static inline bool Nuitka_Cell_Check(PyObject *object) { return Py_TYPE(object) == &Nuitka_Cell_Type; }
static inline bool Nuitka_CellOrPyCell_Check(PyObject *object) {
    return Nuitka_Cell_Check(object) || PyCell_Check(object);
}

struct Nuitka_CellObject {
    /* Python object folklore: */
    PyObject_HEAD

        /* Content of the cell or NULL when empty */
        PyObject *ob_ref;
};

// Create cell with out value, and with or without reference given.
extern struct Nuitka_CellObject *Nuitka_Cell_NewEmpty(void);
extern struct Nuitka_CellObject *Nuitka_Cell_New0(PyObject *value);
extern struct Nuitka_CellObject *Nuitka_Cell_New1(PyObject *value);

// Check stuff while accessing a compile cell in debug mode.
#if defined(Py_GIL_DISABLED)
// Without the GIL, other threads may write the cell at any time: a plain read
// is only good for a test against NULL, a value to use is read with a
// reference, see "Nuitka_Cell_GET_REF".
#define Nuitka_Cell_GET(cell) _Py_atomic_load_ptr_relaxed(&((struct Nuitka_CellObject *)(cell))->ob_ref)
#elif defined(__NUITKA_NO_ASSERT__)
#define Nuitka_Cell_GET(cell) (((struct Nuitka_CellObject *)(cell))->ob_ref)
#else
#define Nuitka_Cell_GET(cell)                                                                                          \
    (CHECK_OBJECT(cell), assert(Nuitka_Cell_Check((PyObject *)cell)), (((struct Nuitka_CellObject *)(cell))->ob_ref))
#endif

NUITKA_MAY_BE_UNUSED static inline PyObject *Nuitka_CellOrPyCell_GET(PyObject *cell) {
    CHECK_OBJECT(cell);
    assert(Nuitka_CellOrPyCell_Check(cell));

#ifdef Py_GIL_DISABLED
    return _Py_atomic_load_ptr_relaxed(&((struct Nuitka_CellObject *)cell)->ob_ref);
#else
    return ((struct Nuitka_CellObject *)cell)->ob_ref;
#endif
}

// The value of a compiled or uncompiled cell with a reference of our own. As
// CPython's "PyCell_GetRef" does, it is taken under the cell's lock without the
// GIL, so a thread replacing the value cannot release it first.
NUITKA_MAY_BE_UNUSED static inline PyObject *Nuitka_CellOrPyCell_GET_REF(PyObject *cell) {
    CHECK_OBJECT(cell);
    assert(Nuitka_CellOrPyCell_Check(cell));

    PyObject *result;
#ifdef Py_GIL_DISABLED
    Py_BEGIN_CRITICAL_SECTION(cell);
    result = _Py_XNewRefWithLock(((struct Nuitka_CellObject *)cell)->ob_ref);
    Py_END_CRITICAL_SECTION();
#else
    result = ((struct Nuitka_CellObject *)cell)->ob_ref;
    Py_XINCREF(result);
#endif
    return result;
}

// Store a value, taking over the reference, and return the previous one to be
// released by the caller. As CPython's "PyCell_SetTakeRef" does, the exchange
// happens under the cell's lock without the GIL, so two threads writing never
// both release the same previous value, and no reader is between the two.
NUITKA_MAY_BE_UNUSED static inline PyObject *Nuitka_CellOrPyCell_EXCHANGE(PyObject *cell, PyObject *value) {
    CHECK_OBJECT(cell);
    CHECK_OBJECT_X(value);
    assert(Nuitka_CellOrPyCell_Check(cell));

    PyObject *old;
#ifdef Py_GIL_DISABLED
    Py_BEGIN_CRITICAL_SECTION(cell);
    old = ((struct Nuitka_CellObject *)cell)->ob_ref;
    _Py_atomic_store_ptr_release(&((struct Nuitka_CellObject *)cell)->ob_ref, value);
    Py_END_CRITICAL_SECTION();
#else
    old = ((struct Nuitka_CellObject *)cell)->ob_ref;
    ((struct Nuitka_CellObject *)cell)->ob_ref = value;
#endif
    return old;
}

#if _DEBUG_REFCOUNTS
extern int count_active_Nuitka_Cell_Type;
extern int count_allocated_Nuitka_Cell_Type;
extern int count_released_Nuitka_Cell_Type;
#endif

NUITKA_MAY_BE_UNUSED static inline void Nuitka_Cell_SET(struct Nuitka_CellObject *cell_object, PyObject *value) {
    CHECK_OBJECT_X(value);
    CHECK_OBJECT(cell_object);

    assert(Nuitka_Cell_Check((PyObject *)cell_object));
#ifdef Py_GIL_DISABLED
    _Py_atomic_store_ptr_release(&cell_object->ob_ref, value);
#else
    cell_object->ob_ref = value;
#endif
}

NUITKA_MAY_BE_UNUSED static inline void Nuitka_CellOrPyCell_SET(PyObject *cell, PyObject *value) {
    CHECK_OBJECT_X(value);
    CHECK_OBJECT(cell);

    assert(Nuitka_CellOrPyCell_Check(cell));
#ifdef Py_GIL_DISABLED
    _Py_atomic_store_ptr_release(&((struct Nuitka_CellObject *)cell)->ob_ref, value);
#else
    ((struct Nuitka_CellObject *)cell)->ob_ref = value;
#endif
}

#endif

//     Part of "Nuitka", an optimizing Python compiler that is compatible and
//     integrates with CPython, but also works on its own.
//
//     Licensed under the GNU Affero General Public License, Version 3 (the "License");
//     you may not use this file except in compliance with the License.
//     You may obtain a copy of the License at
//
//        https://www.gnu.org/licenses/agpl-3.0.txt
//
//     See also: "Nuitka Runtime Library Exception, Version 1.0" in file
//     "LICENSE-RUNTIME.txt" for additional permissions granted under Section 7.
//
//     Unless required by applicable law or agreed to in writing, software
//     distributed under the License is distributed on an "AS IS" BASIS,
//     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//     See the License for the specific language governing permissions and
//     limitations under the License.
