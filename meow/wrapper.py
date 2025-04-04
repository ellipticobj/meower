#!/usr/bin/env python3
import sys
from shlex import quote
from os import environ, path
from subprocess import run

def main():
    """entry point"""
    # get the original command line with quotes preserved
    originalcmdline = sys.argv[0] + " " + " ".join(quote(arg) for arg in sys.argv[1:])

    # set an environment variable with the original command
    environ["ORIGINAL_CMDLINE"] = originalcmdline
    
    # flag to detect keyboard interruption handling
    environ["MEOW_INTERRUPT_HANDLED"] = "0"

    # get the main module path (this will be different when compiled)
    if getattr(sys, 'frozen', False):
        # running as compiled executable
        main_module = sys.executable
    else:
        # running as script
        main_module = '-m'
        environ["PYTHONPATH"] = path.dirname(path.dirname(path.abspath(__file__)))

    # execute the main module
    if main_module == '-m':
        args = [sys.executable, main_module, 'meow.main'] + sys.argv[1:]
    else:
        args = [main_module] + sys.argv[1:]

    try:
        result = run(args)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        # only print interrupt message if it hasn't been handled downstream
        if environ.get("MEOW_INTERRUPT_HANDLED") == "0":
            print("\noperation cancelled by user")
        sys.exit(1)

if __name__ == "__main__":
    main()