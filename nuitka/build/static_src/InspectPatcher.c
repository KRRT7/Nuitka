//     Copyright 2026, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file

/**
 * This is responsible for updating parts of CPython to better work with Nuitka
 * by replacing CPython implementations with enhanced versions.
 */

/* This file is included from another C file, help IDEs to still parse it on its own. */
#ifdef __IDE_ONLY__
#include "nuitka/prelude.h"
#endif

#if PYTHON_VERSION >= 0x300
static PyObject *module_inspect;
#if PYTHON_VERSION >= 0x350
static PyObject *module_types;
#endif
#if PYTHON_VERSION >= 0x3d0
static PyObject *module_interpreters;
#endif
#if PYTHON_VERSION >= 0x380
static PyObject *module_testcapi;
#endif

static char *kw_list_object[] = {(char *)"object", NULL};

// spell-checker: ignore getgeneratorstate, getcoroutinestate

static PyObject *old_getgeneratorstate = NULL;

static PyObject *_inspect_getgeneratorstate_replacement(PyObject *self, PyObject *args, PyObject *kwds) {
    PyObject *object;

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:getgeneratorstate", kw_list_object, &object, NULL)) {
        return NULL;
    }

    CHECK_OBJECT(object);

    if (Nuitka_Generator_Check(object)) {
        struct Nuitka_GeneratorObject *generator = (struct Nuitka_GeneratorObject *)object;

        if (generator->m_running) {
            return PyObject_GetAttrString(module_inspect, "GEN_RUNNING");
        } else if (generator->m_status == status_Finished) {
            return PyObject_GetAttrString(module_inspect, "GEN_CLOSED");
        } else if (generator->m_status == status_Unused) {
            return PyObject_GetAttrString(module_inspect, "GEN_CREATED");
        } else {
            return PyObject_GetAttrString(module_inspect, "GEN_SUSPENDED");
        }
    } else {
        return old_getgeneratorstate->ob_type->tp_call(old_getgeneratorstate, args, kwds);
    }
}

#if PYTHON_VERSION >= 0x350
static PyObject *old_getcoroutinestate = NULL;

static PyObject *_inspect_getcoroutinestate_replacement(PyObject *self, PyObject *args, PyObject *kwds) {
    PyObject *object;

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:getcoroutinestate", kw_list_object, &object, NULL)) {
        return NULL;
    }

    if (Nuitka_Coroutine_Check(object)) {
        struct Nuitka_CoroutineObject *coroutine = (struct Nuitka_CoroutineObject *)object;

        if (coroutine->m_running) {
            return PyObject_GetAttrString(module_inspect, "CORO_RUNNING");
        } else if (coroutine->m_status == status_Finished) {
            return PyObject_GetAttrString(module_inspect, "CORO_CLOSED");
        } else if (coroutine->m_status == status_Unused) {
            return PyObject_GetAttrString(module_inspect, "CORO_CREATED");
        } else {
            return PyObject_GetAttrString(module_inspect, "CORO_SUSPENDED");
        }
    } else {
        return old_getcoroutinestate->ob_type->tp_call(old_getcoroutinestate, args, kwds);
    }
}

static PyObject *old_types_coroutine = NULL;

static char *kw_list_coroutine[] = {(char *)"func", NULL};

static PyObject *_types_coroutine_replacement(PyObject *self, PyObject *args, PyObject *kwds) {
    PyObject *func;

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:coroutine", kw_list_coroutine, &func, NULL)) {
        return NULL;
    }

    if (Nuitka_Function_Check(func)) {
        struct Nuitka_FunctionObject *function = (struct Nuitka_FunctionObject *)func;

        if (function->m_code_object->co_flags & CO_GENERATOR) {
            function->m_code_object->co_flags |= 0x100;
        }
    }

    return old_types_coroutine->ob_type->tp_call(old_types_coroutine, args, kwds);
}

#endif

#endif

#if PYTHON_VERSION >= 0x3d0
static PyObject *old_interpreters_run_func = NULL;

static char *kw_list_run_func[] = {(char *)"id", (char *)"func", (char *)"shared", (char *)"restrict", NULL};

static int _checkInterpretersSharedKeys(PyObject *shared) {
    if (shared == NULL) {
        return 0;
    }

    Py_ssize_t pos = 0;
    PyObject *key;
    PyObject *value;

    while (PyDict_Next(shared, &pos, &key, &value)) {
        if (PyUnicode_Check(key) && PyUnicode_AsUTF8(key) == NULL) {
            return -1;
        }
    }

    return 0;
}

static PyObject *_interpreters_run_func_replacement(PyObject *self, PyObject *args, PyObject *kwds) {
    PyObject *id;
    PyObject *func;
    PyObject *shared = NULL;
    int restricted = 0;

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "OO|O!$p:_interpreters.run_func", kw_list_run_func, &id, &func,
                                     &PyDict_Type, &shared, &restricted)) {
        return NULL;
    }

    if (!Nuitka_Function_Check(func)) {
        return PyObject_Call(old_interpreters_run_func, args, kwds);
    }

    if (_checkInterpretersSharedKeys(shared) < 0) {
        return NULL;
    }

    PyObject *code_object = (PyObject *)((struct Nuitka_FunctionObject *)func)->m_code_object;

    PyObject *replacement_args =
        shared == NULL ? PyTuple_Pack(2, id, code_object) : PyTuple_Pack(3, id, code_object, shared);
    if (unlikely(replacement_args == NULL)) {
        return NULL;
    }

    PyObject *replacement_kwds = NULL;

    if (restricted) {
        replacement_kwds = PyDict_New();
        if (unlikely(replacement_kwds == NULL)) {
            Py_DECREF(replacement_args);
            return NULL;
        }

        if (unlikely(PyDict_SetItemString(replacement_kwds, "restrict", Py_True) < 0)) {
            Py_DECREF(replacement_args);
            Py_DECREF(replacement_kwds);
            return NULL;
        }
    }

    PyObject *result = PyObject_Call(old_interpreters_run_func, replacement_args, replacement_kwds);

    Py_DECREF(replacement_args);
    Py_XDECREF(replacement_kwds);

    return result;
}
#endif

#if PYTHON_VERSION >= 0x380
static PyObject *old_testcapi_function_setvectorcall = NULL;

static PyObject *_testcapi_overridden_vectorcall(struct Nuitka_FunctionObject *function, PyObject *const *stack,
                                                 size_t nargsf, PyObject *kw_names) {
    return Nuitka_String_FromString("overridden");
}

static PyObject *_testcapi_function_setvectorcall_replacement(PyObject *self, PyObject *args) {
    PyObject *func;

    if (!PyArg_ParseTuple(args, "O:function_setvectorcall", &func)) {
        return NULL;
    }

    if (!Nuitka_Function_Check(func)) {
        return PyObject_Call(old_testcapi_function_setvectorcall, args, NULL);
    }

    ((struct Nuitka_FunctionObject *)func)->m_vectorcall = (vectorcallfunc)_testcapi_overridden_vectorcall;

    Py_RETURN_NONE;
}
#endif

#if PYTHON_VERSION >= 0x300
static PyMethodDef _method_def_inspect_getgeneratorstate_replacement = {
    "getgeneratorstate", CAST_METHOD_KW(_inspect_getgeneratorstate_replacement), METH_VARARGS | METH_KEYWORDS, NULL};

#if PYTHON_VERSION >= 0x350
static PyMethodDef _method_def_inspect_getcoroutinestate_replacement = {
    "getcoroutinestate", CAST_METHOD_KW(_inspect_getcoroutinestate_replacement), METH_VARARGS | METH_KEYWORDS, NULL};

static PyMethodDef _method_def_types_coroutine_replacement = {"coroutine", CAST_METHOD_KW(_types_coroutine_replacement),
                                                              METH_VARARGS | METH_KEYWORDS, NULL};

#endif

#if PYTHON_VERSION >= 0x3d0
static PyMethodDef _method_def_interpreters_run_func_replacement = {
    "run_func", CAST_METHOD_KW(_interpreters_run_func_replacement), METH_VARARGS | METH_KEYWORDS, NULL};
#endif

#if PYTHON_VERSION >= 0x380
static PyMethodDef _method_def_testcapi_function_setvectorcall_replacement = {
    "function_setvectorcall", _testcapi_function_setvectorcall_replacement, METH_VARARGS, NULL};
#endif

#if PYTHON_VERSION >= 0x3c0

static char *kw_list_depth[] = {(char *)"depth", NULL};

static bool Nuitka_FrameIsCompiled(_PyInterpreterFrame *frame) {
    return ((frame->frame_obj != NULL) && Nuitka_Frame_Check((PyObject *)frame->frame_obj));
}

static bool Nuitka_FrameIsIncomplete(_PyInterpreterFrame *frame) {
    bool r = _PyFrame_IsIncomplete(frame);

    return r;
}

static PyObject *orig_sys_getframemodulename = NULL;

static PyObject *_sys_getframemodulename_replacement(PyObject *self, PyObject *args, PyObject *kwds) {
    PyObject *depth_arg = NULL;

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:_getframemodulename", kw_list_depth, &depth_arg)) {
        return NULL;
    }

    PyObject *index_value = Nuitka_Number_IndexAsLong(depth_arg ? depth_arg : const_int_0);

    if (unlikely(index_value == NULL)) {
        return NULL;
    }

    Py_ssize_t depth_ssize = PyLong_AsSsize_t(index_value);

    Py_DECREF(index_value);

    PyThreadState *tstate = _PyThreadState_GET();

    _PyInterpreterFrame *frame = CURRENT_TSTATE_INTERPRETER_FRAME(tstate);
    while ((frame != NULL) && ((Nuitka_FrameIsIncomplete(frame)) || depth_ssize-- > 0)) {
        frame = frame->previous;
    }

    if ((frame != NULL) && (Nuitka_FrameIsCompiled(frame))) {
        PyObject *frame_globals = PyObject_GetAttrString((PyObject *)frame->frame_obj, "f_globals");

        PyObject *result = LOOKUP_ATTRIBUTE(tstate, frame_globals, const_str_plain___name__);
        Py_DECREF(frame_globals);

        return result;
    }

    return CALL_FUNCTION_WITH_SINGLE_ARG(tstate, orig_sys_getframemodulename, depth_arg);
}

// spell-checker: ignore getframemodulename
static PyMethodDef _method_def_sys_getframemodulename_replacement = {
    "getcoroutinestate", CAST_METHOD_KW(_sys_getframemodulename_replacement), METH_VARARGS | METH_KEYWORDS, NULL};

#endif

/* Replace inspect functions with ones that handle compiles types too. */
void patchInspectModule(PyThreadState *tstate) {
    static bool is_done = false;
    if (is_done) {
        return;
    }

    CHECK_OBJECT(dict_builtin);

#if PYTHON_VERSION >= 0x300
#if _NUITKA_EXE_MODE && !_NUITKA_STANDALONE_MODE
    // May need to import the "site" module, because otherwise the patching can
    // fail with it being unable to load it (yet)
    if (Py_NoSiteFlag == 0) {
        PyObject *site_module =
            IMPORT_MODULE5(tstate, const_str_plain_site, Py_None, Py_None, const_tuple_empty, const_int_0);

        if (site_module == NULL) {
            // Ignore "ImportError", having a "site" module is not a must.
            CLEAR_ERROR_OCCURRED(tstate);
        }
    }
#endif

    // TODO: Change this into an import hook that is executed after it is imported.
    module_inspect = IMPORT_MODULE5(tstate, const_str_plain_inspect, Py_None, Py_None, const_tuple_empty, const_int_0);

    if (module_inspect == NULL) {
        PyErr_PrintEx(0);
        Py_Exit(1);
    }
    CHECK_OBJECT(module_inspect);

    // Patch "inspect.getgeneratorstate" unless it is already patched.
    old_getgeneratorstate = PyObject_GetAttrString(module_inspect, "getgeneratorstate");
    CHECK_OBJECT(old_getgeneratorstate);

    PyObject *inspect_getgeneratorstate_replacement =
        PyCFunction_New(&_method_def_inspect_getgeneratorstate_replacement, NULL);
    CHECK_OBJECT(inspect_getgeneratorstate_replacement);

    PyObject_SetAttrString(module_inspect, "getgeneratorstate", inspect_getgeneratorstate_replacement);

#if PYTHON_VERSION >= 0x350
    // Patch "inspect.getcoroutinestate" unless it is already patched.
    old_getcoroutinestate = PyObject_GetAttrString(module_inspect, "getcoroutinestate");
    CHECK_OBJECT(old_getcoroutinestate);

    if (PyFunction_Check(old_getcoroutinestate)) {
        PyObject *inspect_getcoroutinestate_replacement =
            PyCFunction_New(&_method_def_inspect_getcoroutinestate_replacement, NULL);
        CHECK_OBJECT(inspect_getcoroutinestate_replacement);

        PyObject_SetAttrString(module_inspect, "getcoroutinestate", inspect_getcoroutinestate_replacement);
    }

    module_types = IMPORT_MODULE5(tstate, const_str_plain_types, Py_None, Py_None, const_tuple_empty, const_int_0);

    if (module_types == NULL) {
        PyErr_PrintEx(0);
        Py_Exit(1);
    }
    CHECK_OBJECT(module_types);

    // Patch "types.coroutine" unless it is already patched.
    old_types_coroutine = PyObject_GetAttrString(module_types, "coroutine");
    CHECK_OBJECT(old_types_coroutine);

    if (PyFunction_Check(old_types_coroutine)) {
        PyObject *types_coroutine_replacement = PyCFunction_New(&_method_def_types_coroutine_replacement, NULL);
        CHECK_OBJECT(types_coroutine_replacement);

        PyObject_SetAttrString(module_types, "coroutine", types_coroutine_replacement);
    }

    static char const *wrapper_enhancement_code = "\n\
import types\n\
_old_GeneratorWrapper = types._GeneratorWrapper\n\
class GeneratorWrapperEnhanced(_old_GeneratorWrapper):\n\
    def __init__(self, gen):\n\
        _old_GeneratorWrapper.__init__(self, gen)\n\
\n\
        if hasattr(gen, 'gi_code'):\n\
            if gen.gi_code.co_flags & 0x0020:\n\
                self._GeneratorWrapper__isgen = True\n\
\n\
types._GeneratorWrapper = GeneratorWrapperEnhanced\n"
#if PYTHON_VERSION >= 0x3b0
                                                  "\
import inspect\n\
_old_get_code_position = inspect._get_code_position\n\
def _get_code_position(code, instruction_index):\n\
    try:\n\
        return _old_get_code_position(code, instruction_index)\n\
    except StopIteration:\n\
        return None, None, None, None\n\
inspect._get_code_position=_get_code_position\n\
"
#endif
        ;

    PyObject *wrapper_enhancement_code_object = Py_CompileString(wrapper_enhancement_code, "<exec>", Py_file_input);
    CHECK_OBJECT(wrapper_enhancement_code_object);

    {
        NUITKA_MAY_BE_UNUSED PyObject *module =
            PyImport_ExecCodeModule("nuitka_types_patch", wrapper_enhancement_code_object);
        CHECK_OBJECT(module);

        NUITKA_MAY_BE_UNUSED bool bool_res = Nuitka_DelModuleString(tstate, "nuitka_types_patch");
        assert(bool_res != false);
    }

#endif

#endif

#if PYTHON_VERSION >= 0x3d0
    module_interpreters = PyImport_ImportModule("_interpreters");

    if (module_interpreters == NULL) {
        CLEAR_ERROR_OCCURRED(tstate);
    } else {
        old_interpreters_run_func = PyObject_GetAttrString(module_interpreters, "run_func");
        CHECK_OBJECT(old_interpreters_run_func);

        PyObject *interpreters_run_func_replacement =
            PyCFunction_New(&_method_def_interpreters_run_func_replacement, NULL);
        CHECK_OBJECT(interpreters_run_func_replacement);

        int set_attr_result =
            PyObject_SetAttrString(module_interpreters, "run_func", interpreters_run_func_replacement);
        Py_DECREF(interpreters_run_func_replacement);

        if (unlikely(set_attr_result < 0)) {
            return;
        }
    }
#endif

#if PYTHON_VERSION >= 0x380
    module_testcapi = PyImport_ImportModule("_testcapi");

    if (module_testcapi == NULL) {
        CLEAR_ERROR_OCCURRED(tstate);
    } else {
        old_testcapi_function_setvectorcall = PyObject_GetAttrString(module_testcapi, "function_setvectorcall");

        if (old_testcapi_function_setvectorcall == NULL) {
            CLEAR_ERROR_OCCURRED(tstate);
        } else {
            PyObject *function_setvectorcall_replacement =
                PyCFunction_New(&_method_def_testcapi_function_setvectorcall_replacement, NULL);
            CHECK_OBJECT(function_setvectorcall_replacement);

            int set_attr_result =
                PyObject_SetAttrString(module_testcapi, "function_setvectorcall", function_setvectorcall_replacement);
            Py_DECREF(function_setvectorcall_replacement);

            if (unlikely(set_attr_result < 0)) {
                return;
            }
        }
    }
#endif

#if PYTHON_VERSION >= 0x3c0
    orig_sys_getframemodulename = Nuitka_SysGetObject("_getframemodulename");

    PyObject *sys_getframemodulename_replacement =
        PyCFunction_New(&_method_def_sys_getframemodulename_replacement, NULL);
    CHECK_OBJECT(sys_getframemodulename_replacement);

    Nuitka_SysSetObject("_getframemodulename", sys_getframemodulename_replacement);
#endif

    is_done = true;
}
#endif

static richcmpfunc original_PyType_tp_richcompare = NULL;

static PyObject *Nuitka_type_tp_richcompare(PyObject *a, PyObject *b, int op) {
    if (likely(op == Py_EQ || op == Py_NE)) {
        if (a == (PyObject *)&Nuitka_Function_Type) {
            a = (PyObject *)&PyFunction_Type;
        } else if (a == (PyObject *)&Nuitka_Method_Type) {
            a = (PyObject *)&PyMethod_Type;
        } else if (a == (PyObject *)&Nuitka_Generator_Type) {
            a = (PyObject *)&PyGen_Type;
#if PYTHON_VERSION >= 0x350
        } else if (a == (PyObject *)&Nuitka_Coroutine_Type) {
            a = (PyObject *)&PyCoro_Type;
#endif
#if PYTHON_VERSION >= 0x360
        } else if (a == (PyObject *)&Nuitka_Asyncgen_Type) {
            a = (PyObject *)&PyAsyncGen_Type;
#endif
        }

        if (b == (PyObject *)&Nuitka_Function_Type) {
            b = (PyObject *)&PyFunction_Type;
        } else if (b == (PyObject *)&Nuitka_Method_Type) {
            b = (PyObject *)&PyMethod_Type;
        } else if (b == (PyObject *)&Nuitka_Generator_Type) {
            b = (PyObject *)&PyGen_Type;
#if PYTHON_VERSION >= 0x350
        } else if (b == (PyObject *)&Nuitka_Coroutine_Type) {
            b = (PyObject *)&PyCoro_Type;
#endif
#if PYTHON_VERSION >= 0x360
        } else if (b == (PyObject *)&Nuitka_Asyncgen_Type) {
            b = (PyObject *)&PyAsyncGen_Type;
#endif
        }
    }

    CHECK_OBJECT(a);
    CHECK_OBJECT(b);

    assert(original_PyType_tp_richcompare);

    return original_PyType_tp_richcompare(a, b, op);
}

void patchTypeComparison(void) {
    if (original_PyType_tp_richcompare == NULL) {
        original_PyType_tp_richcompare = PyType_Type.tp_richcompare;
        PyType_Type.tp_richcompare = Nuitka_type_tp_richcompare;
    }
}

#include "nuitka/freelists.h"

#if PYTHON_VERSION < 0x3e0
// Freelist setup
#define MAX_TRACEBACK_FREE_LIST_COUNT 1000
static PyTracebackObject *free_list_tracebacks = NULL;
static int free_list_tracebacks_count = 0;
#endif

// Create a traceback for a given frame, using a free list hacked into the
// existing type.
PyTracebackObject *MAKE_TRACEBACK(struct Nuitka_FrameObject *frame, int lineno) {
#if 0
    PRINT_STRING("MAKE_TRACEBACK: Enter");
    PRINT_ITEM((PyObject *)frame);
    PRINT_NEW_LINE();

    dumpFrameStack();
#endif

    CHECK_OBJECT(frame);
    if (lineno == 0) {
        lineno = frame->m_frame.f_lineno;
    }
    assert(lineno != 0);

    PyTracebackObject *result;

#if PYTHON_VERSION < 0x3e0
    allocateFromFreeListFixed(free_list_tracebacks, PyTracebackObject, PyTraceBack_Type);
#else
    result = PyObject_GC_New(PyTracebackObject, &PyTraceBack_Type);
    if (unlikely(result == NULL)) {
        return NULL;
    }
#endif

    result->tb_next = NULL;
    result->tb_frame = (PyFrameObject *)frame;
    Py_INCREF(frame);

    result->tb_lasti = -1;
    result->tb_lineno = lineno;

    Nuitka_GC_Track(result);

    return result;
}

#if PYTHON_VERSION < 0x3e0
static void Nuitka_tb_dealloc(PyTracebackObject *tb) {
    // Need to use official method as it checks for recursion.
    Nuitka_GC_UnTrack(tb);

#if 0
#if PYTHON_VERSION >= 0x380
    Py_TRASHCAN_BEGIN(tb, Nuitka_tb_dealloc);
#else
    Py_TRASHCAN_SAFE_BEGIN(tb);
#endif
#endif

    Py_XDECREF(tb->tb_next);
    Py_XDECREF(tb->tb_frame);

    releaseToFreeList(free_list_tracebacks, tb, MAX_TRACEBACK_FREE_LIST_COUNT);

#if 0
#if PYTHON_VERSION >= 0x380
    Py_TRASHCAN_END;
#else
    Py_TRASHCAN_SAFE_END(tb);
#endif
#endif
}

void patchTracebackDealloc(void) { PyTraceBack_Type.tp_dealloc = (destructor)Nuitka_tb_dealloc; }
#else
void patchTracebackDealloc(void) {}
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
