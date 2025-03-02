from os import getcwd
from tqdm import tqdm
from sys import exit, argv
from colorama import Fore, Style, init
from typing import List, Optional, TypeAlias, Final
from argparse import ArgumentParser, Namespace
from loaders import startloadinganimation, stoploadinganimation, ThreadEventTuple
from helpers import completebar, initcommands, validateargs, commithelper, pushhelper
from loggers import success, error, info, printcmd, printinfo, printsteps, ProgressBar
from subprocess import list2cmdline, run as runsubprocess, CompletedProcess, CalledProcessError

# initialize colorama
init(autoreset=True)

VERSION: Final[str] = "0.2.5-preview1"
ArgParser: TypeAlias = ArgumentParser
StepsList: TypeAlias = List[str]
minimal = Namespace(
    cont=False, 
    dry=False, 
    verbose=True, 
    quiet=False, 
    mainpbar=None
)

def pullhandler(args: Namespace) -> None:
    '''handles git pull operations'''
    pull: List[str] = ["git", "pull"]
    if args.norebase:
        pull.append("--no-rebase")
    if args.pull or args.norebase:
        if hasattr(args, 'mainpbar'): # checks of the main bar exists
            runcmd(cmd=pull, flags=args, mainpbar=args.mainpbar)
        else:
            runcmd(cmd=pull, flags=args, mainpbar=args.mainpbar)

def parseoutput(result: CompletedProcess[bytes], flags: Namespace, pbar: ProgressBar, mainpbar: Optional[ProgressBar]) -> None:
    outputstr: str = result.stdout.decode('utf-8', errors='replace').strip()
    pbar.n = 80
    pbar.refresh()
    if outputstr:
        if flags.verbose:
            # output everything
            info(f"    i {Fore.CYAN}{outputstr}", mainpbar)
        else:
            # check for specific outputs
            if 'Everything up-to-date' in outputstr:
                info(f"    i {Fore.CYAN}everything up-to-date", mainpbar)
            elif 'nothing to commit' in outputstr:
                info(f"    i {Fore.CYAN}nothing to commit", mainpbar)
            elif 'create mode' in outputstr or 'delete mode' in outputstr:
                # show additions/deletions
                outputl: List[str] = outputstr.split('\n')
                for line in outputl: # make sure everything is indented properly
                    info(f"    i {Fore.BLACK}{line}", mainpbar)
            elif len(outputstr) < 200:  # show short messages
                if flags.message in outputstr: # dont duplicate commit message
                    pass
                else:
                    info(f"    i {Fore.BLACK}{outputstr}", mainpbar)

def runcmdwithoutprogress(cmd: List[str], mainpbar: Optional[ProgressBar], captureoutput: bool = True) -> CompletedProcess[bytes]:
    result: CompletedProcess[bytes] = runsubprocess(cmd, check=True, cwd=getcwd(), capture_output=captureoutput)
    # parse output
    outputstr: str = result.stdout.decode('utf-8', errors='replace').strip()
    if outputstr:
        # if args.verbose:
        #     outputl = outputstr.split('\n')
        #     for line in outputl:
        #         info(f'    i {Fore.CYAN}{line}', mainpbar)
        # check for specific outputs
        if 'Everything up-to-date' in outputstr:
            info(f"    i {Fore.CYAN}everything up to date", mainpbar)
        elif 'nothing to commit' in outputstr:
            info(f"    i {Fore.CYAN}nothing to commit", mainpbar)
        elif len(outputstr) < 200:  # short messages
            info(f"    i {Fore.BLACK}{outputstr}", mainpbar)

    success("  ✓ completed successfully", mainpbar)
    return result

def runcmd(cmd: List[str], flags: Namespace = minimal, mainpbar: Optional[ProgressBar] = None, keepbar: bool = False, captureoutput=True) -> Optional[CompletedProcess[bytes]]:
    '''executes a command with error handling'''
    cwd: str = getcwd()
    cmdstr: str = list2cmdline(cmd)

    if flags.dry:
        printcmd(cmdstr, mainpbar)
        return None

    try:
        info("  running command:", mainpbar)
        printcmd(f"    $ {cmdstr}", mainpbar)

        # capture output to parse relevant messages
        cmdargs: List[str] = cmd.copy()
        result: Optional[CompletedProcess[bytes]]

        with tqdm(total=100, desc=f"{Fore.CYAN}mrrping...{Style.RESET_ALL}", bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}', position=1, leave=keepbar) as pbar:
            pbar.update(10)
            animationmessage: str = f"executing {cmdstr}..."
            if cmdstr == "git log":
                animationmessage = "q to exit: "
            elif cmdstr.startswith("git commit"):
                animationmessage = "committing...\n"

            animation: ThreadEventTuple = startloadinganimation(animationmessage)

            result = runsubprocess(cmdargs, check=True, cwd=cwd, capture_output=captureoutput)
            pbar.n = 50
            pbar.refresh()

            stoploadinganimation(animation)

            if result:
                parseoutput(result, flags, pbar, mainpbar)

            pbar.n = 100
            pbar.colour = 'green'
            pbar.refresh()
            success("  ✓ completed successfully", mainpbar)

            return result

    except CalledProcessError as e:
        error(f"\n❌ command failed with exit code {e.returncode}:", mainpbar)
        printcmd(f"  $ {cmdstr}", mainpbar)

        if e.stdout:
            info(f"{Fore.BLACK}{e.stdout.decode('utf-8', errors='replace')}", mainpbar)

        if e.stderr:
            error(f"{Fore.RED}{e.stderr.decode('utf-8', errors='replace')}", mainpbar)

        if not flags.cont:
            exit(e.returncode)
        else:
            info(f"{Fore.CYAN}continuing...")
        return None

def checkargv(args: List[str], parser: ArgParser) -> None:
    knowncmds: List[str] = ['push', 'pull', 'commit', 'add', 'log', 'clone', 'branch', 'checkout', 'status', 'fetch', 'merge', 'rebase', 'stash']

    if len(args) != 1:
        # fancy header
        print(f"{Fore.MAGENTA}{Style.BRIGHT}meow {Style.RESET_ALL}{Fore.CYAN}v{VERSION}{Style.RESET_ALL}")

    if len(args) == 1:
        parser.print_help()
        print(f"\ncurrent directory: {Style.BRIGHT}{getcwd()}")
        exit(1)
    elif len(args) == 2:
        if args[1] == "meow":
            print(f"{Fore.MAGENTA}{Style.BRIGHT}meow meow :3{Style.RESET_ALL}")
            exit(0)
        else:
            print(f"\ncurrent directory: {Style.BRIGHT}{getcwd()}")
    
    if len(argv) > 1 and argv[1] in knowncmds:
        argvs: List[str] = argv[2:]
        cmd: List[str] = ["git", argv[1]] + argvs
        

        runcmd(cmd=cmd, captureoutput=False)
        return

def getsteps(args: Namespace) -> StepsList:
    steps: StepsList = []

    if args.status:
        steps.append("status check")

    if args.updatesubmodules:
        steps.append("update submodules")

    if args.stash:
        steps.append("stash changes")

    if args.pull or args.norebase:
        steps.append("pull from remote")

    steps.append("stage changes")

    if args.diff:
        steps.append("show diff")

    steps.append("commit changes")

    if not args.nopush:
        steps.append("push to remote")

    return steps

def checkstatus(args: Namespace, progressbar: ProgressBar) -> bool:
    # status check
    if args.status:
        info(f"{Style.BRIGHT}status check{Style.RESET_ALL}", progressbar)
        cmd: List[str] = ["git", "status"]
        runcmdwithoutprogress(cmd=cmd, mainpbar=progressbar)
        progressbar.update(1)
        return True
    return False

def updatesubmodules(args: Namespace, progressbar: ProgressBar) -> bool:
    if args.updatesubmodules:
        info(f"\n{Style.BRIGHT}updating submodules{Style.RESET_ALL}", progressbar)
        cmd: List[str] = ["git", "submodule", "update", "--init", "--recursive"]
        runcmd(cmd=cmd, flags=args, mainpbar=progressbar)
        progressbar.update(1)
        return True
    return False

def stashchanges(args: Namespace, progressbar: ProgressBar) -> bool:
    if args.stash:
        info(f"\n{Style.BRIGHT}stashing changes{Style.RESET_ALL}", progressbar)
        cmd: List[str] = ["git", "stash"]
        runcmd(cmd=cmd, flags=args, mainpbar=progressbar)
        progressbar.update(1)
        return True
    return False

def pull(args: Namespace, progressbar: ProgressBar) -> bool:
    if args.pull or args.norebase:
        info(f"\n{Style.BRIGHT}pulling from remote{Style.RESET_ALL}",progressbar)
        # create a copy of args with the progress bar added
        args.mainpbar = progressbar
        pullhandler(args)
        progressbar.update(1)
        return True
    return False

def stage(args: Namespace, progressbar: ProgressBar) -> None:
    info(f"\n{Style.BRIGHT}staging changes{Style.RESET_ALL}", progressbar)
    addcmd: List[str] = ["git", "add", *args.add] if args.add else ["git", "add", "."]
    if args.verbose and not args.quiet:
        addcmd.append("--verbose")
    runcmd(cmd=addcmd, flags=args, mainpbar=progressbar)
    progressbar.update(1)

def diff(args: Namespace, progressbar: ProgressBar) -> bool:
    if args.diff:
        info(f"\n{Style.BRIGHT}showing diff{Style.RESET_ALL}", progressbar)
        cmd: List[str] = ["git", "diff", "--staged"]
        runcmdwithoutprogress(cmd=cmd, mainpbar=progressbar)
        return True
    return False

def commit(args: Namespace, progressbar: ProgressBar) -> None:
    info(f"\n{Style.BRIGHT}committing{Style.RESET_ALL}", progressbar)
    commitcmd: List[str] = commithelper(args)
    runcmd(commitcmd, args, mainpbar=progressbar)
    progressbar.update(1)

def push(pushcmd: Optional[List[str]], args: Namespace, progressbar: ProgressBar) -> bool:
    if pushcmd:
        info(f"\n{Style.BRIGHT}pushing to remote{Style.RESET_ALL}", progressbar)
        runcmd(pushcmd, args, mainpbar=progressbar)
        progressbar.update(1)
        return True
    return False

def main() -> None:
    # start animatior before initialization
    animation: ThreadEventTuple = startloadinganimation("initializing...")

    # init
    parser: ArgParser = ArgumentParser(
        prog="meow",
        epilog=f"{Fore.MAGENTA}{Style.BRIGHT}meow {Style.RESET_ALL}{Fore.CYAN}v{VERSION}{Style.RESET_ALL}"
    )
    initcommands(parser)

    # get args
    args: Namespace = parser.parse_args()

    # stop the animation after initialization
    stoploadinganimation(animation)

    checkargv(argv, parser)

    if args.dry:
        print(f"{Fore.MAGENTA}{Style.BRIGHT}dry run{Style.RESET_ALL}")

    if args.version:
        printinfo(VERSION)

    validateargs(args)

    animation = startloadinganimation("preparing...")

    # display pipeline steps
    steps: StepsList = getsteps(args)

    stoploadinganimation(animation)

    # show pipeline overview
    print(f"\n{Fore.CYAN}{Style.BRIGHT}meows to meow:{Style.RESET_ALL}")

    printsteps(steps)

    # execute pipeline
    with tqdm(total=len(steps), desc=f"{Fore.MAGENTA}meowing...{Style.RESET_ALL}", bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}', position=0, leave=True) as progressbar:
        completedsteps: int = 0
        totalsteps: int = len(steps)

        # statuscheck
        if checkstatus(args, progressbar):
            completedsteps += 1

        # update submodules
        if updatesubmodules(args, progressbar):
            completedsteps += 1

        # stash changes
        if stashchanges(args, progressbar):
            completedsteps += 1

        # pull
        if pull(args, progressbar):
            completedsteps += 1

        # stage changes
        stage(args, progressbar)
        completedsteps += 1

        # diff
        if diff(args, progressbar):
            completedsteps += 1

        # commit
        commit(args, progressbar)
        completedsteps += 1

        # push
        pushl: Optional[List[str]] = pushhelper(args)
        if push(pushl, args, progressbar):
            completedsteps += 1

        # complete progressbar
        completebar(progressbar, totalsteps)

    # success message
    print("\n😺")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}{Style.BRIGHT}operation cancelled by user{Style.RESET_ALL}")
        exit(1)
    except Exception as e:
        print(f"\n\n{Fore.MAGENTA}{Style.BRIGHT}error: {Style.RESET_ALL}{Fore.RED}{e}{Style.RESET_ALL}")
