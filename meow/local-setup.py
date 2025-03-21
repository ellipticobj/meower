from setuptools import setup, Extension # type: ignore
from Cython.Build import cythonize # type: ignore
from Cython.Compiler import Options # type: ignore
from config import VERSION # type: ignore

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

LDFLAGS = [
    "-Wl,--gc-sections",
    "-Wl,--build-id=none",
    "-Wl,-z,norelro",
    "-Wl,--hash-style=sysv",
    "-nostdlib"
]

MACROS = [
    ('PY_SSIZE_T_CLEAN', "1"),
    ('CYTHON_USE_PYLONG_INTERNALS', "0"),  # Not compatible with Python 3.13
    ('CYTHON_FAST_THREAD_STATE', "0"),     # Not compatible with Python 3.13
    ('CYTHON_NO_PYINIT_EXPORT', "1"),
    ('CYTHON_USE_EXC_INFO_STACK', "0"),
    ('CYTHON_USE_TYPE_SLOTS', "1"),        # Use type slots for performance
    ('CYTHON_FAST_PYCALL', "1"),           # Fast Python calls
    ('CYTHON_PROFILE', "0"),               # Disable profiling
    ('CYTHON_TRACE', "0")                  # Disable tracing
]

COMPILERDIRECTIVES={
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


Options.docstrings = False
Options.embed_pos_in_docstring = False

extensions = [
    Extension(
        "meow.utils.helpers", 
        ["utils/helpers.py"],
        extra_compile_args=CFLAGS,
        extra_link_args=LDFLAGS,
        define_macros=MACROS,
    ),
    Extension(
        "meow.utils.loaders",
        ["utils/loaders.py"],
        extra_compile_args=CFLAGS,
        extra_link_args=LDFLAGS,
        define_macros=MACROS
    ),
    Extension(
        "meow.utils.loggers",
        ["utils/loggers.py"],
        extra_compile_args=CFLAGS,
        extra_link_args=LDFLAGS,
        define_macros=MACROS
    ),
    Extension(
        "meow.core.executor",
        ["core/executor.py"],
        extra_compile_args=CFLAGS,
        extra_link_args=LDFLAGS,
        define_macros=MACROS
    ),
    Extension(
        "meow.core.pipeline",
        ["core/pipeline.py"],
        extra_compile_args=CFLAGS,
        extra_link_args=LDFLAGS,
        define_macros=MACROS
    )
]

setup(
    name="meow",
    version=VERSION,
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
    entry_points={"console_scripts": ["meow=meow.main:main"]},
    zip_safe=False
)
