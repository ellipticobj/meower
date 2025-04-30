# local-setup.py
from setuptools import setup, Extension
from Cython.Build import cythonize
from Cython.Compiler import Options
from config import VERSION
import sys

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
    ('CYTHON_USE_PYLONG_INTERNALS', "0"),
    ('CYTHON_FAST_THREAD_STATE', "0"),
    ('CYTHON_NO_PYINIT_EXPORT', "1"),
    ('CYTHON_USE_EXC_INFO_STACK', "0"),
    ('CYTHON_USE_TYPE_SLOTS', "1"),
    ('CYTHON_FAST_PYCALL', "1"),
    ('CYTHON_PROFILE', "0"),
    ('CYTHON_TRACE', "0")
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

if __name__ == "__main__":
    targetbuildfile = None
    if len(sys.argv) > 1 and sys.argv[1] != "build_ext":
        targetbuildfile = sys.argv[-1] # Assume the last argument is the file

    extensionstobuild = []
    if targetbuildfile:
        for ext in extensions:
            if ext.sources[0] == targetbuildfile:
                extensionstobuild.append(ext)
                break
        if not extensionstobuild:
            print(f"error: File '{targetbuildfile}' not found in the defined extensions.")
            sys.exit(1)
    else:
        extensionstobuild = extensions

    setup(
        name="meow",
        version=VERSION,
        ext_modules=cythonize(
            extensionstobuild,
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
