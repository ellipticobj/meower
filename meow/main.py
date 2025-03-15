import sys
from tqdm import tqdm # type: ignore
from colorama import init, Fore, Style # type: ignore
from argparse import ArgumentParser, Namespace
from config import VERSION, KNOWNCOMMANDS, GITCOMMANDMESSAGES # type: ignore
from core.pipeline import Pipeline # type: ignore
from utils.loggers import printinfo, spacer, success # type: ignore
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
        epilog=f"{Fore.MAGENTA}{Style.BRIGHT}meow {Style.RESET_ALL}{Fore.CYAN}v{VERSION}{Style.RESET_ALL}"
    )
    
    initcommands(parser)

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    
    if len(sys.argv) >= 2:  # easter egg
        if sys.argv[1] == "meow":
            print(f"{Fore.MAGENTA}{Style.BRIGHT}meow meow :3{Style.RESET_ALL}")
            sys.exit(0)
        elif sys.argv[1] in KNOWNCOMMANDS:
            handlegitcommands(sys.argv, GITCOMMANDMESSAGES)

    args: Namespace = parser.parse_args()

    # display version if --version
    if args.version:
        printinfo(VERSION)
        sys.exit(0)
    
    # treat arguments as git commands if message is not quoted
    if args.message in KNOWNCOMMANDS:
        handlegitcommands([sys.argv[0]] + args.message, GITCOMMANDMESSAGES)
        sys.exit(0)

    # validate arguments 
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
        pipeline = Pipeline(args=args, steps=steps, pbar=pbar)
        pipeline.run()

        spacer(pbar=pbar)
        
        # generate report
        if args.report:
            pipeline.generatereport(pbar=pbar)
        else:
            # TODO: make this an absolute path | make this configurable
            pipeline.generatereport(saveto="report.txt", pbar=pbar)

    spacer(pbar=pbar)
    success("😺", pbar=pbar)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}{Style.BRIGHT}operation cancelled by user{Style.RESET_ALL}")
        sys.exit(1)