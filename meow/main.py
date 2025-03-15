import sys
import os
from tqdm import tqdm # type: ignore
from colorama import init, Fore, Style # type: ignore
from argparse import ArgumentParser, Namespace
from config import VERSION, KNOWNCOMMANDS, GITCOMMANDMESSAGES # type: ignore
from core.pipeline import Pipeline # type: ignore
from utils.loggers import printinfo, spacer, error, success # type: ignore
from utils.helpers import ( # type: ignore
    validateargs,
    initcommands,
    displayheader,
    displaysteps,
    getpipelinesteps
)
from commands.githandler import handlegitcommands # type: ignore

def main() -> None:
    '''entry point'''
    init(autoreset=True)
    
    parser = ArgumentParser(
        prog="meow",
        description="a friendly git wrapper",
        epilog=f"{Fore.MAGENTA}{Style.BRIGHT}meow {Style.RESET_ALL}{Fore.CYAN}v{VERSION}{Style.RESET_ALL}"
    )
    
    initcommands(parser)

    # show help if no arguments provided
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    
    # check if we're in a git repository
    isgitrepo = os.path.exists(os.path.join(os.getcwd(), '.git')) or os.popen('git rev-parse --is-inside-work-tree 2>/dev/null').read().strip() == 'true'
    
    # handle direct git command syntax: meow <git-command> [args...]
    if len(sys.argv) >= 2:
        # easter egg :3
        if sys.argv[1] == "meow":
            print(f"{Fore.MAGENTA}{Style.BRIGHT}meow meow :3{Style.RESET_ALL}")
            sys.exit(0)
        
        # check for git command
        if sys.argv[1].lower() in KNOWNCOMMANDS:
            # warn if not in a git repo except for commands that can work outside a repo (init, clone, help)
            safecmds = ['init', 'clone', 'help', 'version']
            if not isgitrepo and sys.argv[1].lower() not in safecmds:
                error("not in a git repository")
                error("tip: use 'meow init' to create a new repository")
                sys.exit(1)
            
            # handle git command
            handlegitcommands(sys.argv, GITCOMMANDMESSAGES)

    # parse arguments for pipeline mode
    args: Namespace = parser.parse_args()

    # display version if --version
    if args.version:
        printinfo(VERSION)
        sys.exit(0)
    
    # check if first message argument is a git command
    if args.message and args.message[0] in KNOWNCOMMANDS:
        handlegitcommands([sys.argv[0]] + args.message, GITCOMMANDMESSAGES)
        sys.exit(0)

    # warn if not in a git repo for pipeline mode
    if not isgitrepo:
        error("not in a git repository")
        error("tip: use 'meow init' to create a new repository")
        sys.exit(1)

    # validate pipeline arguments 
    validateargs(args)

    # display header
    displayheader()

    # indicate dry run
    if args.dry:
        print(f"\n{Fore.MAGENTA}{Style.BRIGHT}dry run{Style.RESET_ALL}")

    # get pipeline steps
    steps = getpipelinesteps(args)
    displaysteps(steps)

    # execute pipeline
    with tqdm(
        total=len(steps) + 1,
        desc=f"{Fore.RED}meowing...{Style.RESET_ALL}",
        bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}',
        position=1,
        leave=True
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
            # generate report in current directory (absolute path)
            reportpath = os.path.join(os.getcwd(), "report.txt")
            pipeline.generatereport(saveto=reportpath, pbar=pbar)
        
        # ensure progress bar is closed properly
        pbar.close()
    
    # add final spacing and cat after progress bar context is closed
    spacer()
    success("😺")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}{Style.BRIGHT}operation cancelled by user{Style.RESET_ALL}")
        sys.exit(1)