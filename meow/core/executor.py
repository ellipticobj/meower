from select import select
from tqdm import tqdm  # type: ignore
from argparse import Namespace
from fcntl import fcntl, F_SETFL
from colorama import Fore, Style  # type: ignore
from os import O_NONBLOCK, chdir, getcwd
from typing import List, Optional, Dict, Tuple
from subprocess import Popen, run as runsubprocess, CompletedProcess, CalledProcessError, PIPE

from meow.utils.helpers import suggestfix, list2cmdline  # type: ignore
from meow.utils.loaders import startloadinganimation, stoploadinganimation  # type: ignore
from meow.utils.loggers import error, info, printcmd, printoutput, success, spacer  # type: ignore
from meow.utils.gitutils import getreporoot, getgitcmdenv, rungitcmd  # type: ignore

# constants
PROGRESS_START = 20
PROGRESS_MID = 70
PROGRESS_PUSH_CAP = 95
PROGRESS_END = 100

def _processpushline(line: str, source: str, innerpbar: tqdm, alloutput: List[str]) -> None:
    line = line.strip()
    if not line:
        return

    alloutput.append(line)

    if any(important in line.lower() for important in [
        "error:", "fatal:", "authentication failed",
        "permission denied", "rejected", "failed"
    ]):
        error(f"      {line}", pbar=innerpbar)

    allowedpatterns = {
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
        "Everything up-to-date"
    }
    if any(pattern in line for pattern in allowedpatterns):
        info(f"      {line}", pbar=innerpbar)

    # extract percentage from progress lines
    if "%" in line:
        try:
            percent = int(line.split("%")[0].split()[-1])
            if percent > innerpbar.n:
                innerpbar.n = min(percent, PROGRESS_PUSH_CAP)  # cap at 95% until complete
                innerpbar.refresh()
        except (ValueError, IndexError):
            pass

def handlepush(
        cmd: List[str],
        workdir: str,
        env: Dict[str, str],
        innerpbar: tqdm
) -> Tuple[int, str, str]:
    info("      pushing...", pbar=innerpbar)

    process = Popen(
        cmd,
        cwd=workdir,
        env=env,
        stdout=PIPE,
        stderr=PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    all_output: List[str] = []
    stdout_data, stderr_data = [], []

    try:
        for pipe in [process.stdout, process.stderr]:
            if pipe is not None:
                fcntl(pipe.fileno(), F_SETFL, O_NONBLOCK)

        while True:
            reads = [stream for stream in [process.stdout, process.stderr] if stream]
            if not reads:
                break

            readable, _, _ = select(reads, [], [], 0.1)

            for stream in readable:
                try:
                    line = stream.readline()
                    if not line:
                        reads.remove(stream)
                        continue

                    if stream == process.stdout:
                        stdout_data.append(line)
                        _processpushline(line, "stdout", innerpbar, all_output)
                    else:
                        stderr_data.append(line)
                        _processpushline(line, "stderr", innerpbar, all_output)
                except (IOError, OSError):
                    continue

            if process.poll() is not None and not readable:
                break

        returncode = process.wait()

        if returncode == 0:
            innerpbar.n = PROGRESS_END
            innerpbar.colour = 'green'
            innerpbar.refresh()

            # show final summary
            spacer(pbar=innerpbar)
            status_lines = []
            for line in reversed(all_output):
                if any(pattern in line for pattern in [
                    "->", "new branch", "new tag",
                    "Everything up-to-date"
                ]):
                    status_lines.append(line)
                    if len(status_lines) >= 2:
                        break

            for line in reversed(status_lines):
                success(f"      {line}", pbar=innerpbar)
        else:
            innerpbar.colour = 'red'
            error("      push failed", pbar=innerpbar)

        return (
            returncode,
            "".join(stdout_data),
            "".join(stderr_data)
        )
    except KeyboardInterrupt:
        error("      push interrupted", pbar=innerpbar)
        return 1, "".join(stdout_data), "".join(stderr_data)
    finally:
        process.terminate()

def _rungitcmd(
    gitcmd: List[str],
    env: Dict[str, str],
    inner_progress_bar: tqdm,
    capture_output: bool,
    flags: Optional[Namespace] = None,
    pbar: Optional[tqdm] = None,
) -> CompletedProcess:
    """Runs a non-push git command with progress and error handling."""
    try:
        returncode, stdout, stderr = rungitcmd(gitcmd, env)

        inner_progress_bar.n = PROGRESS_MID
        inner_progress_bar.refresh()

        result = CompletedProcess(
            args=["git"] + gitcmd,
            returncode=returncode,
            stdout=stdout.encode('utf-8') if stdout else b'',
            stderr=stderr.encode('utf-8') if stderr else b''
        )

        if capture_output and stdout:
            printoutput(result=result, flags=flags or Namespace(verbose=False),
                        pbar=inner_progress_bar, mainpbar=pbar)

        inner_progress_bar.n = PROGRESS_END
        inner_progress_bar.colour = 'green'
        inner_progress_bar.refresh()

        if returncode == 0:
            success("    ✓ completed successfully", pbar=inner_progress_bar)
            return result
        else:
            raise CalledProcessError(returncode, result.args, result.stdout, result.stderr)

    except CalledProcessError as e:
        error(f"\n❌ command failed with exit code {e.returncode}:", pbar)
        printcmd(f"  $ {list2cmdline(e.cmd)}", pbar)

        if e.stderr:
            error(f"{Fore.RED}{e.stderr.decode('utf-8', errors='replace')}", pbar)
            suggestion = suggestfix(e.stderr.decode('utf-8', errors='replace'))
            if suggestion:
                error(suggestion, pbar)

        if flags and flags.cont:
            info(f"{Fore.CYAN}continuing despite error...", pbar)
            return CompletedProcess(args=e.args, returncode=e.returncode)
        else:
            raise
    except Exception as e:
        error(f"      Command failed: {str(e)}", pbar=inner_progress_bar)
        return CompletedProcess(
            args=["git"] + gitcmd,
            returncode=1,
            stdout=b'',
            stderr=str(e).encode('utf-8')
        )

def runoptimizedgitcmd(
    cmd: List[str],
    flags: Optional[Namespace] = None,
    pbar: Optional[tqdm] = None,
    withprogress: bool = True,
    captureoutput: bool = True
) -> Optional[CompletedProcess]:
    """
    Optimized function to run git commands, handling credentials and progress.
    """
    if not cmd or len(cmd) < 2 or cmd[0] != "git":
        return runcmd(cmd, flags, pbar, withprogress, captureoutput)

    gitcmd = cmd[1:]
    env = getgitcmdenv()
    workdir = getreporoot() or getcwd()
    chdir(workdir)

    cmdstr = list2cmdline(cmd)

    if flags and flags.dry:
        printcmd(cmdstr, pbar)
        return None

    spacer(pbar=pbar)
    info("    running command:", pbar)
    printcmd(f"      $ {cmdstr}", pbar)

    animation = None
    inner_progress_bar = None
    try:
        if withprogress:
            with tqdm(
                total=PROGRESS_END,
                desc=f"{Fore.CYAN}  mrrping...{Style.RESET_ALL}",
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}',
                position=0,
                leave=False
            ) as inner_progress_bar:
                inner_progress_bar.n = PROGRESS_START
                animation = startloadinganimation()

                if cmd[1] == "push":
                    returncode, stdout, stderr = handlepush(cmd, workdir, env, inner_progress_bar)
                    result = CompletedProcess(
                        args=cmd,
                        returncode=returncode,
                        stdout=stdout.encode('utf-8') if stdout else b'',
                        stderr=stderr.encode('utf-8') if stderr else b''
                    )
                else:
                    result = _rungitcmd(gitcmd, env, inner_progress_bar, captureoutput, flags, pbar)

                return result
        else:
            returncode, stdout, stderr = rungitcmd(gitcmd, env)
            result = CompletedProcess(
                args=cmd,
                returncode=returncode,
                stdout=stdout.encode('utf-8') if stdout else b'',
                stderr=stderr.encode('utf-8') if stderr else b''
            )
            if returncode == 0:
                if captureoutput and stdout:
                    printoutput(result, flags or Namespace(verbose=False), pbar, pbar)
                success("    ✓ completed successfully", pbar=pbar)
                return result
            else:
                raise CalledProcessError(returncode, result.args, result.stdout, result.stderr)

    except CalledProcessError as e:
        error(f"\n❌ command failed with exit code {e.returncode}:", pbar)
        printcmd(f"  $ {cmdstr}", pbar)

        if e.stderr:
            error(f"{Fore.RED}{e.stderr.decode('utf-8', errors='replace')}", pbar)
            suggestion = suggestfix(e.stderr.decode('utf-8', errors='replace'))
            if suggestion:
                error(suggestion, pbar)

        if flags and flags.cont:
            info(f"{Fore.CYAN}continuing despite error...", pbar)
            return None
        else:
            raise
    except Exception as e:
        error(f"      Command failed: {str(e)}", pbar=inner_progress_bar)
        return CompletedProcess(
            args=cmd,
            returncode=1,
            stdout=b'',
            stderr=str(e).encode('utf-8')
        )
    finally:
        if animation:
            stoploadinganimation(threadinfo=animation)
        if inner_progress_bar:
            inner_progress_bar.close()

def runcmd(
    cmd: List[str],
    flags: Optional[Namespace] = None,
    pbar: Optional[tqdm] = None,
    withprogress: bool = True,
    captureoutput: bool = True,
    printsuccess: bool = True,
    isinteractive: Optional[bool] = None,
    env: Optional[Dict[str, str]] = None
) -> Optional[CompletedProcess]:
    """
    Executes a command, handling progress, output, and errors.
    """
    flags = flags or Namespace(dry=False, cont=False, verbose=False)

    if not cmd:
        return None

    if len(cmd) > 1 and cmd[0] == "git" and not isinteractive:
        return runoptimizedgitcmd(
            cmd=cmd,
            flags=flags,
            pbar=pbar,
            withprogress=withprogress,
            captureoutput=captureoutput
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
        elif isgitcmd and len(cmd) >= 2:
            if cmd[1] == "commit" and len(cmd) == 2:
                interactive = True

        cmdenv: Dict[str, str] = env or {}
        if isgitcmd:
            gitenv = getgitcmdenv()
            cmdenv.update(gitenv)

        workdir = getreporoot() if isgitcmd else getcwd()

        if interactive:
            result = runsubprocess(
                cmd,
                check=True,
                cwd=workdir,
                capture_output=False,
                env=cmdenv
            )
            return result

        animation = None
        innerpbar = None
        if withprogress:
            with tqdm(
                total=PROGRESS_END,
                desc=f"{Fore.CYAN}  mrrping...{Style.RESET_ALL}",
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}',
                position=0,
                leave=False
            ) as innerpbar:
                innerpbar.n = PROGRESS_START
                animation = startloadinganimation()

                result = runsubprocess(
                    cmd,
                    check=True,
                    cwd=workdir,
                    stdout=PIPE if captureoutput else None,
                    stderr=PIPE if captureoutput else None,
                    env=cmdenv
                )

                innerpbar.n = PROGRESS_MID
                innerpbar.refresh()
                stoploadinganimation(threadinfo=animation)

                if captureoutput and result.stdout:
                    printoutput(result=result, flags=flags, pbar=innerpbar, mainpbar=pbar)

                innerpbar.n = PROGRESS_END
                innerpbar.colour = 'green'
                innerpbar.refresh()

                if printsuccess:
                    success("    ✓ completed successfully", pbar=innerpbar)

                return result

        result = runsubprocess(
            cmd,
            check=True,
            cwd=workdir,
            stdout=PIPE if captureoutput else None,
            stderr=PIPE if captureoutput else None,
            env=cmdenv
        )

        if captureoutput and result.stdout:
            printoutput(result, flags, pbar, pbar)

        if printsuccess:
            success("    ✓ completed successfully", pbar=pbar)

        return result

    except CalledProcessError as e:
        error(f"\n❌ command failed with exit code {e.returncode}:", pbar)
        printcmd(f"  $ {cmdstr}", pbar)

        outstr = e.stdout.decode('utf-8', errors='replace') if e.stdout else ""
        errstr = e.stderr.decode('utf-8', errors='replace') if e.stderr else ""

        if outstr:
            info(f"{Fore.BLACK}{outstr}", pbar)
        if errstr:
            error(f"{Fore.RED}{errstr}", pbar)
            suggestion = suggestfix(errstr)
            if suggestion:
                error(suggestion, pbar)

        if not flags.cont:
            raise
        else:
            info(f"{Fore.CYAN}continuing despite error...", pbar)
            return None
    except KeyboardInterrupt:
        error("user interrupted", pbar)
        return None
    finally:
        if animation:
            stoploadinganimation(threadinfo=animation)
        if innerpbar:
            innerpbar.close()
