from setuptools import setup, Extension # type: ignore
from Cython.Build import cythonize # type: ignore
from Cython.Compiler import Options # type: ignore
from config import VERSION # type: ignore

CFLAGS = [
    "-Oz", 
    "-flto=4", 
    "-fno-ident", 
    "-fmerge-all-constants",
    "-fno-unwind-tables",
    "-fno-asynchronous-unwind-tables",
    "-march=native"
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
    ('CYTHON_USE_PYLONG_INTERNALS', "0"),
    ('CYTHON_FAST_THREAD_STATE', "0"),
    ('CYTHON_NO_PYINIT_EXPORT', "1"),
    ('CYTHON_USE_EXC_INFO_STACK', "0")
]

COMPILERDIRECTIVES={
    'language_level': "3",
    'boundscheck': False,
    'wraparound': False,
    'initializedcheck': False,
    'nonecheck': False,
    'cdivision': True,
    'optimize.unpack_method_calls': True,
    'optimize.inline_defnode_calls': True,
    'optimize.use_switch': True,
    'c_api_binop_methods': False
}


Options.docstrings = False
Options.embed_pos_in_docstring = False

extensions = [
    Extension(
        "helpers", 
        ["utils/helpers.py"],
        extra_compile_args=CFLAGS,
        extra_link_args=LDFLAGS,
        define_macros=MACROS,
    ),
    Extension(
        "loaders",
        ["utils/loaders.py"],
        extra_compile_args=CFLAGS,
        extra_link_args=LDFLAGS,
        define_macros=MACROS
    ),
    Extension(
        "loggers",
        ["utils/loggers.py"],
        extra_compile_args=CFLAGS,
        extra_link_args=LDFLAGS,
        define_macros=MACROS
    ),
    Extension(
        "executor",
        ["core/executor.py"],
        extra_compile_args=CFLAGS,
        extra_link_args=LDFLAGS,
        define_macros=MACROS
    ),
    Extension(
        "pipeline",
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
        nthreads=4
    ),
    entry_points={"console_scripts": ["meow=main:main"]},
    zip_safe=False
)
