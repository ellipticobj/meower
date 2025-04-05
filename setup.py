from setuptools import setup, Extension
from Cython.Build import cythonize
from Cython.Compiler import Options

# Compiler directives for Cython
COMPILERDIRECTIVES = {
    'language_level': "3",
    'boundscheck': False,
    'wraparound': True,
    'initializedcheck': False,
    'nonecheck': False,
    'cdivision': True,
    'cdivision_warnings': False,
    'optimize.unpack_method_calls': True,
    'optimize.inline_defnode_calls': True,
    'optimize.use_switch': True,
    'infer_types': True,
    'c_api_binop_methods': False,
    'fast_getattr': True
}

# Compiler flags
CFLAGS = [
    "-O3",
    "-fno-ident",
    "-fmerge-all-constants",
    "-fno-unwind-tables",
    "-fno-asynchronous-unwind-tables",
    "-funroll-loops",
    "-ffunction-sections",
    "-fdata-sections",
    "-pipe"
]

# Linker flags
LDFLAGS = [
    "-Wl,--gc-sections",
    "-Wl,--build-id=none",
]

# Macros
MACROS = [
    ('PY_SSIZE_T_CLEAN', "1"),
    ('CYTHON_USE_PYLONG_INTERNALS', "0"),
    ('CYTHON_FAST_THREAD_STATE', "0"),
    ('CYTHON_NO_PYINIT_EXPORT', "1"),
    ('CYTHON_USE_EXC_INFO_STACK', "0"),
    ('CYTHON_USE_TYPE_SLOTS', "1"),
    ('CYTHON_FAST_PYCALL', "1"),
    ('CYTHON_PROFILE', "0"),
    ('CYTHON_TRACE', "0")
]

# Disable docstrings for smaller binaries
Options.docstrings = False
Options.embed_pos_in_docstring = False

# Define extensions
extensions = [
    Extension(
        "meow.utils.helpers",
        ["meow/utils/helpers.py"],
        extra_compile_args=CFLAGS,
        extra_link_args=LDFLAGS,
        define_macros=MACROS,
    ),
    Extension(
        "meow.utils.loaders",
        ["meow/utils/loaders.py"],
        extra_compile_args=CFLAGS,
        extra_link_args=LDFLAGS,
        define_macros=MACROS
    ),
    Extension(
        "meow.utils.loggers",
        ["meow/utils/loggers.py"],
        extra_compile_args=CFLAGS,
        extra_link_args=LDFLAGS,
        define_macros=MACROS
    ),
    Extension(
        "meow.core.executor",
        ["meow/core/executor.py"],
        extra_compile_args=CFLAGS,
        extra_link_args=LDFLAGS,
        define_macros=MACROS
    ),
    Extension(
        "meow.core.pipeline",
        ["meow/core/pipeline.py"],
        extra_compile_args=CFLAGS,
        extra_link_args=LDFLAGS,
        define_macros=MACROS
    )
]

setup(
    ext_modules=cythonize(
        extensions,
        compiler_directives=COMPILERDIRECTIVES,
        exclude=[
            "**/__init__.py",
            "**/tests/*",
            "setup.py"
        ],
        build_dir="build/cython",
        nthreads=8
    ),
    include_package_data=True,
    zip_safe=False,
)
