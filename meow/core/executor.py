from sys import exit
from select import select
from tqdm import tqdm  # type: ignore
from argparse import Namespace
from fcntl import fcntl, F_SETFL
from os import O_NONBLOCK, chdir, getcwd, strerror
from typing import List, Optional, Dict, Tuple, Any
from subprocess import Popen, CompletedProcess, CalledProcessError, PIPE, run as runsubprocess
from colorama import Fore, Style # type: ignore
from time import time
from threading import Thread

from meow.utils.helpers import displayerror, list2cmdline  # type: ignore
from meow.utils.loaders import startloadinganimation, stoploadinganimation  # type: ignore
from meow.utils.loggers import error, info, printcmd, printoutput, success, spacer  # type: ignore
from meow.utils.gitutils import getreporoot, getgitcmdenv, rungitcmd  # type: ignore

# constants for progress bar and output filtering
PROGRESS_TOTAL = 100
PROGRESS_INITIAL = 20
PROGRESS_FINAL = 95
PUSH_PROGRESS_UPDATE_INTERVAL = 0.1
ALLOWED_PUSH_PATTERNS = {
    "->",
    "To ",
    "Total",
    "* [new",
    "remote:",
    "! [rejected]",
    "Writing objects:",
    "Counting objects:",
    "Enumerating objects:",
    "Compressing objects:",
    "Everything up-to-date",
}

# Type alias for better readability
CommandResult = Optional[CompletedProcess]
StrList = List[str]


def handlepush(
    cmd: StrList,
    workdir: str,
    env: Dict[str, str],
    innerpbar: tqdm,
) -> Tuple[int, str, str]:
    process = Popen(
        cmd,
        cwd=workdir,
        env=env,
        stdout=PIPE,
        stderr=PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )

    alloutput: StrList = []
    stdoutbuff: StrList = []
    stderrbuff: StrList = []
    lastprogressupdatetime = time()
    
    def process_output(line: str, source: str) -> None:
        line = line.strip()
        if not line:
            return

        alloutput.append(line)

        if any(
            important in line.lower()
            for important in [
                "error:",
                "fatal:",
                "authentication failed",
                "permission denied",
                "rejected",
                "failed",
            ]
        ):
            error(f"  {line}", pbar=innerpbar)

        if any(pattern in line for pattern in ALLOWED_PUSH_PATTERNS):
            info(f"  {line}", pbar=innerpbar)

        if "%" in line:
            try:
                percent = int(line.split("%")[0].split()[-1])
                if percent > innerpbar.n:
                    innerpbar.n = min(percent, PROGRESS_FINAL)
                    innerpbar.refresh()
            except (ValueError, IndexError):
                pass

    def read_output(stream: Any, buffer: StrList, source: str) -> None:
        try:
            line = stream.readline()
            if line:
                buffer.append(line)
                process_output(line, source)
        except (IOError, OSError) as e:
            error(f"error reading from {source}: {e}", pbar=innerpbar)

    for pipe in [process.stdout, process.stderr]:
        if pipe:
            try:
                fcntl(pipe.fileno(), F_SETFL, O_NONBLOCK)
            except OSError as e:
                error(f"error setting non-blocking mode: {e}", pbar=innerpbar)
                exit(1)

    # use threads for reading stdout and stderr
    stdoutthread = Thread(
        target=read_output, args=(process.stdout, stdoutbuff, "stdout")
    )
    stderrthread = Thread(
        target=read_output, args=(process.stderr, stderrbuff, "stderr")
    )
    stdoutthread.start()
    stderrthread.start()

    # main loop for reading output and checking process status
    while True:
        reads = [stream for stream in [process.stdout, process.stderr] if stream]
        if not reads:
            break

        try:
            readable, _, _ = select(reads, [], [], 0.1)
        except OSError as e:
            error(f"Error during select: {e}", pbar=innerpbar)
            break  # exit the loop on select error

        if process.poll() is not None:
            break

        # update progress bar periodically, even if no new output
        currentline = time()
        if currentline - lastprogressupdatetime >= PUSH_PROGRESS_UPDATE_INTERVAL:
            innerpbar.refresh()
            lastprogressupdatetime = currentline

    # wait for threads to finish reading any remaining output
    stdoutthread.join()
    stderrthread.join()

    returncode = process.wait()

    if returncode == 0:
        innerpbar.n = PROGRESS_TOTAL
        innerpbar.colour = "green"
        innerpbar.refresh()

        spacer(pbar=innerpbar)
        statuslines: StrList = []
        for line in reversed(alloutput):
            if any(
                pattern in line
                for pattern in [
                    "->",
                    "new branch",
                    "new tag",
                    "Everything up-to-date",
                ]
            ):
                statuslines.append(line)
                if len(statuslines) >= 2:
                    break

        for line in reversed(statuslines):
            success(f"  {line}", pbar=innerpbar)
    else:
        innerpbar.colour = "red"
        error("  push failed", pbar=innerpbar)

    return (
        returncode,
        "".join(stdoutbuff),
        "".join(stderrbuff),
    )


def runoptimizedgitcmd(
    cmd: StrList,
    flags: Optional[Namespace] = None,
    pbar: Optional[tqdm] = None,
    withprogress: bool = True,
    captureoutput: bool = True,
) -> CommandResult:
    if not cmd or len(cmd) < 2 or cmd[0] != "git":
        # not a git command; use the standard runcmd
        return runcmd(cmd, flags, pbar, withprogress, captureoutput)

    # extract the git command (without "git" prefix)
    gitcmd = cmd[1:]

    # get the environment with git credential handling
    env = getgitcmdenv()

    # determine the working directory (git root if available)
    workdir = getreporoot()
    if workdir:
        try:
            chdir(workdir)  # change to the git repository root
        except OSError as e:
            error(f"Error changing directory to {workdir}: {e}", pbar=pbar)
            exit(1)

    else:
        workdir = getcwd()

    # format the command string for display
    cmdstr = list2cmdline(cmd)

    if flags and flags.dry:
        printcmd(list2cmdline(cmd), pbar)
        return None

    # log command execution
    spacer(pbar=pbar)
    info("    running command:", pbar)
    printcmd(f"      $ {cmdstr}", pbar)

    returncode: int = 0
    stdout: str = ""
    stderr: str = ""
    animation: Any = None

    try:
        if withprogress:
            with tqdm(
                total=PROGRESS_TOTAL,
                desc=f"{Fore.CYAN}  mrrping...{Style.RESET_ALL}",
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}',
                position=0,
                leave=False,
            ) as innerpbar:
                innerpbar.n = PROGRESS_INITIAL
                animation = startloadinganimation(pbar=innerpbar)  # store the animation thread

                if cmd[1] == "push":
                    returncode, stdout, stderr = handlepush(
                        cmd, workdir, env, innerpbar
                    )
                    result = CompletedProcess(
                        args=cmd,
                        returncode=returncode,
                        stdout=stdout.encode("utf-8") if stdout else b"",
                        stderr=stderr.encode("utf-8") if stderr else b"",
                    )
                else:
                    # execute non-push git commands
                    returncode, stdout, stderr = rungitcmd(gitcmd, env)
                    innerpbar.n = 70
                    innerpbar.refresh()
                    stoploadinganimation(
                        threadinfo=animation
                    )  # stop animation

                    result = CompletedProcess(
                        args=cmd,
                        returncode=returncode,
                        stdout=stdout.encode("utf-8") if stdout else b"",
                        stderr=stderr.encode("utf-8") if stderr else b"",
                    )

                    if captureoutput and stdout:
                        printoutput(
                            result=result,
                            flags=flags or Namespace(verbose=False),
                            pbar=innerpbar,
                            mainpbar=pbar,
                        )

                innerpbar.n = PROGRESS_TOTAL
                innerpbar.colour = "green"
                innerpbar.refresh()
                innerpbar.close()

                if returncode == 0:
                    success("    ✓ completed successfully", pbar=innerpbar)
                    return result
                else:
                    error(f"\n❌ command failed with exit code {returncode}:", pbar)
                    printcmd(f"  $ {cmdstr}", pbar)
                    displayerror(stderr, stdout, pbar)

                    if flags and flags.cont:
                        info(f"{Fore.CYAN}continuing despite error...", pbar)
                        return result
                    else:
                        exit(returncode)
        else:  # if not withprogress
            returncode, stdout, stderr = rungitcmd(gitcmd, env)
            result = CompletedProcess(
                args=cmd,
                returncode=returncode,
                stdout=stdout.encode("utf-8") if stdout else b"",
                stderr=stderr.encode("utf-8") if stderr else b"",
            )
            if returncode == 0:
                if captureoutput and stdout:
                    printoutput(
                        result, flags or Namespace(verbose=False), pbar, pbar
                    )
                success("    ✓ completed successfully", pbar=pbar)
                return result
            else:
                error(f"\n❌ command failed with exit code {returncode}:", pbar)
                printcmd(f"  $ {cmdstr}", pbar)
                displayerror(stderr, stdout, pbar)

                if flags and flags.cont:
                    info(f"{Fore.CYAN}continuing despite error...", pbar)
                    return None
                else:
                    exit(returncode)
    except Exception as e:
        error(f"      Command failed: {str(e)}", pbar=pbar)  # changed innerpbar to pbar
        return CompletedProcess(
            args=cmd,
            returncode=1,
            stdout=b"",
            stderr=str(e).encode("utf-8"),
        )
    finally:
        if animation:
            stoploadinganimation(threadinfo=animation)  # ensure animation is stopped

    return result

def runcmd(
    cmd: StrList,
    flags: Optional[Namespace] = None,
    pbar: Optional[tqdm] = None,
    withprogress: bool = True,
    captureoutput: bool = True,
    printsuccess: bool = True,
    isinteractive: Optional[bool] = None,
    env: Optional[Dict[str, str]] = None,
) -> CommandResult:
    """
    executes a command
    """
    flags = flags or Namespace(dry=False, cont=False, verbose=False)
    animation: Any = None

    if not cmd:
        return None

    if len(cmd) > 1 and cmd[0] == "git" and not isinteractive:
        return runoptimizedgitcmd(
            cmd=cmd,
            flags=flags,
            pbar=pbar,
            withprogress=withprogress,
            captureoutput=captureoutput,
        )

    if flags.dry:
        printcmd(list2cmdline(cmd), pbar)
        return None

    cmdstr: str = list2cmdline(cmd)
    isgitcmd: bool = len(cmd) > 1 and cmd[0] == "git"

    try:
        spacer(pbar=pbar)
        info("    running command:", pbar)
        printcmd(f"      $ {cmdstr}", pbar)

        interactive: bool = False
        if isinteractive is not None:
            interactive = isinteractive
        elif isgitcmd and len(cmd) == 2 and cmd[1] == "commit":
            interactive = True

        cmdenv: Dict[str, str] = env or {}
        if isgitcmd:
            gitenv = getgitcmdenv()
            cmdenv.update(gitenv)

        # handle interactive commands directly
        if interactive: 
            workdir = getreporoot() if isgitcmd else getcwd()
            result = runsubprocess(
                cmd,
                check=True,
                cwd=workdir,
                capture_output=False,
                env=cmdenv,
            )
            return result

        if withprogress:
            with tqdm(
                total=PROGRESS_TOTAL,
                desc=f"{Fore.CYAN}  mrrping...{Style.RESET_ALL}",
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}',
                position=0,
                leave=False,
            ) as innerpbar:
                innerpbar.n = PROGRESS_INITIAL
                animation = startloadinganimation(pbar=innerpbar)

                workdir = getreporoot() if isgitcmd else getcwd()
                result = runsubprocess(
                    cmd,
                    check=True,
                    cwd=workdir,
                    stdout=PIPE if captureoutput else None,
                    stderr=PIPE if captureoutput else None,
                    env=cmdenv,
                )

                innerpbar.n = 70
                innerpbar.refresh()
                stoploadinganimation(threadinfo=animation)

                if result and captureoutput and result.stdout:
                    printoutput(
                        result=result,
                        flags=flags,
                        pbar=innerpbar,
                        mainpbar=pbar,
                    )

                innerpbar.n = PROGRESS_TOTAL
                innerpbar.colour = "green"
                innerpbar.refresh()
                innerpbar.close()

                if printsuccess:
                    success("    ✓ completed successfully", pbar=innerpbar)
                return result
        else:  # if not withprogress
            workdir = getreporoot() if isgitcmd else getcwd()
            result = runsubprocess(
                cmd,
                check=True,
                cwd=workdir,
                stdout=PIPE if captureoutput else None,
                stderr=PIPE if captureoutput else None,
                env=cmdenv,
            )
            if result and captureoutput and result.stdout:
                printoutput(result, flags, pbar, pbar)
            if printsuccess:
                success("    ✓ completed successfully", pbar=pbar)
            return result

    except CalledProcessError as e:
        error(f"\n❌ command failed with exit code {e.returncode}:", pbar)
        printcmd(f"  $ {list2cmdline(e.cmd)}", pbar)
        outstr = e.stdout.decode("utf-8", errors="replace") if e.stdout else ""
        errstr = e.stderr.decode("utf-8", errors="replace") if e.stderr else ""

        displayerror(errstr, outstr, pbar)

        if not flags.cont:
            exit(e.returncode)
        else:
            info(f"{Fore.CYAN}continuing despite error...", pbar)
        return None
    except OSError as e:
        if e.errno is not None:
            error(f"OSError: {e}  errno: {e.errno} {strerror(e.errno)}", pbar)
        else:
            error(f"OSError: {e}", pbar)
        return None
    except KeyboardInterrupt:
        error("user interrupted", pbar)
        return None
    finally:
        if animation:
            stoploadinganimation(animation)  # ensure that the animation is stopped.
        # no need to close pbar here.

