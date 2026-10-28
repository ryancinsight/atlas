.. Exact API declarations from NumPy v2.5.4, source revision
   a3d0ef1df045b858e68115001fdabc930bb3b68c.
   doc/source/reference/c-api/types-and-structures.rst:
   PyArrayObject members, PyArray_ArrFuncs callbacks, PyArrayMethod_Spec,
   and PyArrayMethod_StridedLoop typedef; datetimes.rst: datetime metadata.
   Narrative and unrelated declarations omitted; native nesting preserved.

.. c:type:: PyArrayObject

   .. c:member:: char *data

   .. c:member:: PyObject *base

   .. c:member:: int flags

.. c:type:: PyArray_ArrFuncs

    .. c:member:: PyObject *getitem(void *data, void *arr)

    .. c:member:: int setitem(PyObject *item, void *data, void *arr)

    .. c:member:: void copyswapn( \
            void *dest, npy_intp dstride, void *src, npy_intp sstride, \
            npy_intp n, int swap, void *arr)

    .. c:member:: void copyswap(void *dest, void *src, int swap, void *arr)

    .. c:member:: int compare(const void* d1, const void* d2, void* arr)

    .. c:member:: int argmax( \
            void* data, npy_intp n, npy_intp* max_ind, void* arr)

    .. c:member:: void dotfunc( \
            void* ip1, npy_intp is1, void* ip2, npy_intp is2, void* op, \
            npy_intp n, void* arr)

    .. c:member:: int scanfunc(FILE* fd, void* ip, void* arr)

    .. c:member:: int fromstr(char* str, void* ip, char** endptr, void* arr)

    .. c:member:: npy_bool nonzero(void* data, void* arr)

    .. c:member:: void fill(void* data, npy_intp length, void* arr)

    .. c:member:: void fillwithscalar( \
            void* buffer, npy_intp length, void* value, void* arr)

    .. c:member:: int sort(void* start, npy_intp length, void* arr)

    .. c:member:: int argsort( \
            void* start, npy_intp* result, npy_intp length, void *arr)

    .. c:member:: NPY_SCALARKIND scalarkind(PyArrayObject* arr)

    .. c:member:: int argmin( \
            void* data, npy_intp n, npy_intp* min_ind, void* arr)

.. c:type:: PyArrayMethod_Spec

   .. c:member:: NPY_ARRAYMETHOD_FLAGS flags

.. c:type:: PyArray_DatetimeMetaData

   .. c:member:: NPY_DATETIMEUNIT base

.. c:type:: int (PyArrayMethod_StridedLoop)(PyArrayMethod_Context *context, \
        char *const *data, const npy_intp *dimensions, const npy_intp *strides, \
        NpyAuxData *auxdata)
