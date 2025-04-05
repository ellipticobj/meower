#!/usr/bin/env python3
"""
Simplified test version of meow main.py
This file can be used to test if PyInstaller packaging works correctly
"""

import sys
import os
from argparse import ArgumentParser
from colorama import init, Fore, Style

# Version for testing
VERSION = "1.2.0-test"

def main():
    """Entry point for the application"""
    init(autoreset=True)
    
    parser = ArgumentParser(
        prog="meow",
        description="A friendly git wrapper",
        epilog=f"{Fore.MAGENTA}{Style.BRIGHT}meow {Style.RESET_ALL}{Fore.CYAN}v{VERSION}{Style.RESET_ALL}"
    )
    
    # Add basic arguments
    parser.add_argument("--version", action="store_true", help="show version and exit")
    parser.add_argument("--meow", action="store_true", help="meow :3")
    
    # Show help if no arguments provided
    if len(sys.argv) == 1:
        parser.print_help()
        return 0
    
    # Parse arguments
    args = parser.parse_args()
    
    # Display version if --version
    if args.version:
        print(f"meow version {VERSION}")
        return 0
    
    # Easter egg :3
    if args.meow:
        print(f"{Fore.MAGENTA}{Style.BRIGHT}meow meow :3{Style.RESET_ALL}")
        return 0
    
    # Print system info for debugging
    print(f"Python version: {sys.version}")
    print(f"Platform: {sys.platform}")
    print(f"Executable: {sys.executable}")
    print(f"Current directory: {os.getcwd()}")
    
    print(f"\n{Fore.GREEN}Test successful! The executable is working.{Style.RESET_ALL}")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}{Style.BRIGHT}Operation cancelled by user{Style.RESET_ALL}")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n{Fore.RED}{Style.BRIGHT}Error: {e}{Style.RESET_ALL}")
        sys.exit(1)
