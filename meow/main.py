from sys import path, argv, exit
from os import path as ospath
from argparse import ArgumentParser, Namespace

from tqdm import tqdm # type: ignore
from colorama import init, Fore, Style # type: ignore

from meow.utils.loggers import success # type: ignore
from typing import List

try:
    # when running as a module: python -m meow.main
    from meow.config import VERSION, KNOWNCOMMANDS, GITCOMMANDMESSAGES
    from meow.core.pipeline import Pipeline
    from meow.utils.loggers import printinfo, spacer, error
    from meow.utils.helpers import (
        validateargs,
        initcommands,
        displayheader,
        displaysteps,
        getpipelinesteps
    )
    from meow.commands.githandler import handlegitcommands
    from meow.utils.gitutils import isgitrepo as checkisgitrepo
except ModuleNotFoundError:
    # when running directly: python main.py
    path.insert(0, ospath.abspath(ospath.join(ospath.dirname(__file__), '..')))
    
    from meow.config import VERSION, KNOWNCOMMANDS, GITCOMMANDMESSAGES
    from meow.core.pipeline import Pipeline
    from meow.utils.loggers import printinfo, spacer, error
    from meow.utils.helpers import (
        validateargs,
        initcommands,
        displayheader,
        displaysteps,
        getpipelinesteps
    )
    from meow.commands.githandler import handlegitcommands
    from meow.utils.gitutils import isgitrepo as checkisgitrepo

def main() -> None:
    '''entry point'''
    init(autoreset=True)
    
    parser: ArgumentParser = ArgumentParser(
        prog="meow",
        description="a friendly git wrapper",
        epilog=f"{Fore.MAGENTA}{Style.BRIGHT}meow {Style.RESET_ALL}{Fore.CYAN}v{VERSION}{Style.RESET_ALL}"
    )
    
    initcommands(parser)

    # show help if no arguments provided
    if len(argv) == 1:
        parser.print_help()
        exit(1)
    
    # check if we're in a git repository using our utility function
    isgitrepo: bool = checkisgitrepo()

    # display header
    displayheader()

    # parse arguments for pipeline mode
    args: Namespace = parser.parse_args()

    if args.run:
        # warn if not in a git repo except for commands that can work outside a repo (init, clone, help)
        safecmds: List[str] = ['init', 'clone', 'help', 'version']
        if not isgitrepo and argv[1].lower() not in safecmds:
            error("not in a git repository")
            error("tip: use 'meow init' to create a new repository")
            exit(1)
        
        # handle git command
        handlegitcommands(argv, GITCOMMANDMESSAGES)

    # easter egg :3
    if args.meow:
        print(f"{Fore.MAGENTA}{Style.BRIGHT}meow meow :3{Style.RESET_ALL}")
        exit(0)

    # display version if --version
    if args.version:
        printinfo(VERSION)
        exit(0)
    
    # check if first message argument is a git command
    if args.message and args.message[0] in KNOWNCOMMANDS:
        handlegitcommands([argv[0]] + args.message, GITCOMMANDMESSAGES)
        exit(0)

    # warn if not in a git repo for pipeline mode
    if not isgitrepo:
        error("not in a git repository")
        error("use 'meow init' to create a new repository")
        exit(1)

    # validate pipeline arguments 
    validateargs(args)

    # indicate dry run
    if args.dry:
        print(f"\n{Fore.MAGENTA}{Style.BRIGHT}dry run{Style.RESET_ALL}")

    # get pipeline steps
    steps = getpipelinesteps(args)
    displaysteps(steps)

    print(f"\n{Fore.MAGENTA}{Style.BRIGHT}executing{Style.RESET_ALL}")

    # execute pipeline
    with tqdm(
        total=len(steps) + 1,
        desc=f"{Fore.RED}meowing...{Style.RESET_ALL}",
        bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}',
        position=1,
        leave=False
    ) as pbar:
        # create and run pipeline
        pipeline = Pipeline(args=args, steps=steps, pbar=pbar)
        pipeline.run()

        # add spacing after completion
        spacer(pbar=pbar)
        
        # generate report
        if args.report:
            pipeline.generatereport(pbar=pbar)
        else:
            # generate report in config directory (absolute path)
            reportpath: str = ospath.expanduser("~/.config/meow/report.txt")
            pipeline.generatereport(saveto=reportpath, pbar=pbar)
        
        # ensure progress bar is closed properly
        pbar.close()
    
    print()
    success(message="✓ meow is done!")
    print()
    print("😺")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}{Style.BRIGHT}operation cancelled by user{Style.RESET_ALL}")
        exit(1)