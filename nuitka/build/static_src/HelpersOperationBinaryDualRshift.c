//     Copyright 2026, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file

/* WARNING, this code is GENERATED. Modify the template HelperOperationBinaryDual.c.j2 instead! */

/* This file is included from another C file, help IDEs to still parse it on its own. */
#ifdef __IDE_ONLY__
#include "nuitka/prelude.h"
#endif

/* C helpers for type specialized ">>" (RSHIFT) operations */

/* Code referring to "NILONG" corresponds to Nuitka int/long/C long value and "NILONG" to Nuitka int/long/C long value.
 */
bool BINARY_OPERATION_RSHIFT_NILONG_NILONG_NILONG(nuitka_ilong *result, nuitka_ilong *operand1,
                                                  nuitka_ilong *operand2) {
    CHECK_NILONG_OBJECT(operand1);
    CHECK_NILONG_OBJECT(operand2);

    bool left_c_usable = IS_NILONG_C_VALUE_VALID(operand1);
    bool right_c_usable = IS_NILONG_C_VALUE_VALID(operand2);

    if (left_c_usable && right_c_usable) {
        // Not every code path will make use of all possible results.
#if defined(_MSC_VER)
#pragma warning(push)
#pragma warning(disable : 4101)
#endif
        NUITKA_MAY_BE_UNUSED bool cbool_result;
        NUITKA_MAY_BE_UNUSED PyObject *obj_result;
        NUITKA_MAY_BE_UNUSED long clong_result;
        NUITKA_MAY_BE_UNUSED double cfloat_result;
#if defined(_MSC_VER)
#pragma warning(pop)
#endif

        CHECK_NILONG_OBJECT(operand1);
        CHECK_NILONG_OBJECT(operand2);

        const long a = GET_NILONG_C_VALUE(operand1);
        const long b = GET_NILONG_C_VALUE(operand2);

        if (unlikely(b < 0)) {
            PyThreadState *tstate = PyThreadState_GET();

            SET_CURRENT_EXCEPTION_TYPE0_STR(tstate, PyExc_ValueError, "negative shift count");
            goto exit_result_exception;
        }

        /* Short cut for zero shift or shifting zero. */
        if (a == 0 || b == 0) {
            goto exit_result_ok_left;
        } else if (b >= LONG_BIT) {
            if (a < 0) {
                goto exit_result_ok_const_int_neg_1;
            } else {
                goto exit_result_ok_const_int_0;
            }
        } else {
            long r = Py_ARITHMETIC_RIGHT_SHIFT(long, a, b);

            clong_result = r;
            goto exit_result_ok_clong;
        }

    exit_result_ok_clong:
        SET_NILONG_C_VALUE(result, clong_result);
        return true;

    exit_result_ok_left:
        SET_NILONG_C_VALUE(result, GET_NILONG_C_VALUE(operand1));
        return true;

    exit_result_ok_const_int_0:
        SET_NILONG_C_VALUE(result, 0);
        return true;

    exit_result_ok_const_int_neg_1:
        SET_NILONG_C_VALUE(result, -1);
        return true;

    exit_result_exception:
        return false;

    } else if (left_c_usable == false && right_c_usable) {
        PyObject *python_result = BINARY_OPERATION_RSHIFT_OBJECT_LONG_CLONG(operand1->python_value, operand2->c_value);

        if (unlikely(python_result == NULL)) {
            return false;
        }

        SET_NILONG_OBJECT_VALUE(result, python_result);
        return true;
    } else if (left_c_usable && right_c_usable == false) {
        PyObject *python_result = BINARY_OPERATION_RSHIFT_OBJECT_CLONG_LONG(operand1->c_value, operand2->python_value);

        if (unlikely(python_result == NULL)) {
            return false;
        }

        SET_NILONG_OBJECT_VALUE(result, python_result);

        return true;
    } else {
        PyObject *python_result =
            BINARY_OPERATION_RSHIFT_OBJECT_LONG_LONG(operand1->python_value, operand2->python_value);

        if (unlikely(python_result == NULL)) {
            return false;
        }

        SET_NILONG_OBJECT_VALUE(result, python_result);

        return true;
    }
}

/* Code referring to "NILONG" corresponds to Nuitka int/long/C long value and "DIGIT" to C platform digit value for long
 * Python objects. */
bool BINARY_OPERATION_RSHIFT_NILONG_NILONG_DIGIT(nuitka_ilong *result, nuitka_ilong *operand1, long operand2) {
    CHECK_NILONG_OBJECT(operand1);
    assert(Py_ABS(operand2) < (1 << PyLong_SHIFT));

    bool left_c_usable = IS_NILONG_C_VALUE_VALID(operand1);
    bool right_c_usable = true;

    if (left_c_usable && right_c_usable) {
        // Not every code path will make use of all possible results.
#if defined(_MSC_VER)
#pragma warning(push)
#pragma warning(disable : 4101)
#endif
        NUITKA_MAY_BE_UNUSED bool cbool_result;
        NUITKA_MAY_BE_UNUSED PyObject *obj_result;
        NUITKA_MAY_BE_UNUSED long clong_result;
        NUITKA_MAY_BE_UNUSED double cfloat_result;
#if defined(_MSC_VER)
#pragma warning(pop)
#endif

        CHECK_NILONG_OBJECT(operand1);
        assert(Py_ABS(operand2) < (1 << PyLong_SHIFT));

        const long a = GET_NILONG_C_VALUE(operand1);
        const long b = (long)(operand2);

        if (unlikely(b < 0)) {
            PyThreadState *tstate = PyThreadState_GET();

            SET_CURRENT_EXCEPTION_TYPE0_STR(tstate, PyExc_ValueError, "negative shift count");
            goto exit_result_exception;
        }

        /* Short cut for zero shift or shifting zero. */
        if (a == 0 || b == 0) {
            goto exit_result_ok_left;
        } else if (b >= LONG_BIT) {
            if (a < 0) {
                goto exit_result_ok_const_int_neg_1;
            } else {
                goto exit_result_ok_const_int_0;
            }
        } else {
            long r = Py_ARITHMETIC_RIGHT_SHIFT(long, a, b);

            clong_result = r;
            goto exit_result_ok_clong;
        }

    exit_result_ok_clong:
        SET_NILONG_C_VALUE(result, clong_result);
        return true;

    exit_result_ok_left:
        SET_NILONG_C_VALUE(result, GET_NILONG_C_VALUE(operand1));
        return true;

    exit_result_ok_const_int_0:
        SET_NILONG_C_VALUE(result, 0);
        return true;

    exit_result_ok_const_int_neg_1:
        SET_NILONG_C_VALUE(result, -1);
        return true;

    exit_result_exception:
        return false;

    } else if (left_c_usable == false && right_c_usable) {
        PyObject *python_result = BINARY_OPERATION_RSHIFT_OBJECT_LONG_DIGIT(operand1->python_value, operand2);

        if (unlikely(python_result == NULL)) {
            return false;
        }

        SET_NILONG_OBJECT_VALUE(result, python_result);
        return true;
    } else {
        NUITKA_CANNOT_GET_HERE("cannot happen with types NILONG DIGIT");
        return false;
    }
}

/* Code referring to "DIGIT" corresponds to C platform digit value for long Python objects and "NILONG" to Nuitka
 * int/long/C long value. */
bool BINARY_OPERATION_RSHIFT_NILONG_DIGIT_NILONG(nuitka_ilong *result, long operand1, nuitka_ilong *operand2) {
    assert(Py_ABS(operand1) < (1 << PyLong_SHIFT));
    CHECK_NILONG_OBJECT(operand2);

    bool left_c_usable = true;
    bool right_c_usable = IS_NILONG_C_VALUE_VALID(operand2);

    if (left_c_usable && right_c_usable) {
        // Not every code path will make use of all possible results.
#if defined(_MSC_VER)
#pragma warning(push)
#pragma warning(disable : 4101)
#endif
        NUITKA_MAY_BE_UNUSED bool cbool_result;
        NUITKA_MAY_BE_UNUSED PyObject *obj_result;
        NUITKA_MAY_BE_UNUSED long clong_result;
        NUITKA_MAY_BE_UNUSED double cfloat_result;
#if defined(_MSC_VER)
#pragma warning(pop)
#endif

        assert(Py_ABS(operand1) < (1 << PyLong_SHIFT));
        CHECK_NILONG_OBJECT(operand2);

        const long a = (long)(operand1);
        const long b = GET_NILONG_C_VALUE(operand2);

        if (unlikely(b < 0)) {
            PyThreadState *tstate = PyThreadState_GET();

            SET_CURRENT_EXCEPTION_TYPE0_STR(tstate, PyExc_ValueError, "negative shift count");
            goto exit_result_exception;
        }

        /* Short cut for zero shift or shifting zero. */
        if (a == 0 || b == 0) {
            goto exit_result_ok_left;
        } else if (b >= LONG_BIT) {
            if (a < 0) {
                goto exit_result_ok_const_int_neg_1;
            } else {
                goto exit_result_ok_const_int_0;
            }
        } else {
            long r = Py_ARITHMETIC_RIGHT_SHIFT(long, a, b);

            clong_result = r;
            goto exit_result_ok_clong;
        }

    exit_result_ok_clong:
        SET_NILONG_C_VALUE(result, clong_result);
        return true;

    exit_result_ok_left:
        SET_NILONG_C_VALUE(result, (long)(operand1));
        return true;

    exit_result_ok_const_int_0:
        SET_NILONG_C_VALUE(result, 0);
        return true;

    exit_result_ok_const_int_neg_1:
        SET_NILONG_C_VALUE(result, -1);
        return true;

    exit_result_exception:
        return false;

    } else if (left_c_usable && right_c_usable == false) {
        PyObject *python_result = BINARY_OPERATION_RSHIFT_OBJECT_DIGIT_LONG(operand1, operand2->python_value);

        if (unlikely(python_result == NULL)) {
            return false;
        }

        SET_NILONG_OBJECT_VALUE(result, python_result);

        return true;
    } else {
        NUITKA_CANNOT_GET_HERE("cannot happen with types DIGIT NILONG");
        return false;
    }
}

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
