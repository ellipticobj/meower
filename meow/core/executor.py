from sys import exit
import os
from tqdm import tqdm # type: ignore
from argparse import Namespace
from colorama import Fore, Style # type: ignore
from typing import List, Optional, Dict
from subprocess import Popen, run as runsubprocess, CompletedProcess, CalledProcessError, PIPE

from meow.utils.helpers import suggestfix, list2cmdline # type: ignore
from meow.utils.loaders import startloadinganimation, stoploadinganimation # type: ignore
from meow.utils.loggers import error, info, printcmd, printoutput, success, spacer # type: ignore
from meow.utils.gitutils import getreporoot, getgitcmdenv, rungitcmd # type: ignore

# cache for storing command execution times
# commandtimingcache: Dict[str, float] = {}

def runoptimizedgitcmd(
    cmd: List[str],
    flags: Optional[Namespace] = None,
    pbar: Optional[tqdm] = None,
    withprogress: bool = True,
    captureoutput: bool = True
) -> Optional[CompletedProcess]:
    '''
    optimized function to run git commands using GitPython when available
    
    uses the GitRunner class which is more reliable for git credential handling
    '''
    if not cmd or len(cmd) < 2 or cmd[0] != "git":
        # not a git command then use standard runcmd
        return runcmd(cmd, flags, pbar, withprogress, captureoutput)
    
    # get git command (without "git" prefix)
    gitcmd = cmd[1:]
    
    # get environment with git credential handling
    env = getgitcmdenv()
    
    # determine working directory - use git root for git commands if available
    workdir = getreporoot()
    if workdir:
        # Change to git repo root
        os.chdir(workdir)
    
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
    
    if withprogress:
        with tqdm(
            total=100,
            desc=f"{Fore.CYAN}  mrrping...{Style.RESET_ALL}",
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}',
            position=0,
            leave=False
        ) as innerpbar:
            innerpbar.n = 20
            animation = startloadinganimation()

            if cmd[1] == "push":
                process = Popen(
                    cmd,
                    cwd=workdir,
                    env=env,
                    stdout=PIPE,
                    stderr=PIPE,
                    bufsize=1,
                    universal_newlines=True,
                    text=True
                )
                
                stdoutlines = []
                stderrlines = []
                
                while True:
                    # output progress
                    stderrline = process.stderr.readline() if process.stderr else ''
                    if stderrline:
                        stderrlines.append(stderrline)
                        if "Writing objects:" in stderrline \
                            or "Compressing objects:" in stderrline \
                            or "Enumerating objects:" in stderrline \
                            or "Counting objects:" in stderrline:
                            info(f"      {stderrline.strip()}", pbar=innerpbar)
                    
                    stdoutline = process.stdout.readline() if process.stdout else ''
                    if stdoutline:
                        stdoutlines.append(stdoutline)
                    
                    # check if process has finished
                    if process.poll() is not None and not stderrline and not stdoutline:
                        break
                
                if process.stdout:
                    for line in process.stdout:
                        stdoutlines.append(line)
                
                returncode = process.returncode
                stdout = "".join(stdoutlines)
                stderr = "".join(stderrlines)

                output = (stderr + stdout).splitlines()
                if len(output) > 3:
                    # plint lines saying remote blah blah blah at the end
                    lastlines = output[-3:]
                    spacer(pbar=innerpbar)
                    for line in lastlines:
                        if line.strip():
                            info(f"      {line.strip()}", pbar=innerpbar)
                elif len(output) == 1:
                    # print line saying everything up to date
                    spacer(pbar=innerpbar)
                    info(f"      {output[0]}", pbar=innerpbar)
            else:
                # Execute the actual command for non-push git commands
                returncode, stdout, stderr = rungitcmd(gitcmd, env)
                
                innerpbar.n = 70
                innerpbar.refresh()
                stoploadinganimation(threadinfo=animation)
                
                result = CompletedProcess(
                    args=cmd,
                    returncode=returncode,
                    stdout=stdout.encode('utf-8') if stdout else b'',
                    stderr=stderr.encode('utf-8') if stderr else b''
                )
                
                if captureoutput and stdout:
                    printoutput(result=result, flags=flags or Namespace(verbose=False), 
                                pbar=innerpbar, mainpbar=pbar)
                
                innerpbar.n = 100
                innerpbar.colour = 'green'
                innerpbar.refresh()
                innerpbar.close()
                
                if returncode == 0:
                    success("    ✓ completed successfully", pbar=innerpbar)
                    return result
                else:
                    error(f"\n❌ command failed with exit code {returncode}:", pbar)
                    printcmd(f"  $ {cmdstr}", pbar)
                    
                    if stderr:
                        error(f"{Fore.RED}{stderr}", pbar)
                        suggestion = suggestfix(stderr)
                        if suggestion:
                            error(suggestion, pbar)
                    
                    if flags and flags.cont:
                        info(f"{Fore.CYAN}continuing despite error...", pbar)
                        return None
                    else:
                        exit(returncode)
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
            error(f"\n❌ command failed with exit code {returncode}:", pbar)
            printcmd(f"  $ {cmdstr}", pbar)
            
            if stderr:
                error(f"{Fore.RED}{stderr}", pbar)
                suggestion = suggestfix(stderr)
                if suggestion:
                    error(suggestion, pbar)
            
            if flags and flags.cont:
                info(f"{Fore.CYAN}continuing despite error...", pbar)
                return None
            else:
                exit(returncode)
    
    return None

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
    '''
    executes a command
    '''
    # default flags
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

    # print command for dry run
    if flags.dry:
        printcmd(list2cmdline(cmd), pbar)
        return None

    # base command string for logging/caching
    cmdstr: str = list2cmdline(cmd)
    
    # for git commands, check command timing cache to optimize progress display
    isgitcmd: bool = len(cmd) > 1 and cmd[0] == "git"

    try:
        spacer(pbar=pbar)
        info("    running command:", pbar)
        printcmd(f"      $ {cmdstr}", pbar)

        # determine if command should be interactive
        interactive: bool = False
        if isinteractive is not None:
            interactive = isinteractive
        elif isgitcmd and len(cmd) >= 2:
            # git commit with no args is interactive
            if cmd[1] == "commit" and len(cmd) == 2:
                interactive = True

        # enhanced environment variables
        cmdenv: Dict[str, str] = env or {}
        
        # For git commands, enhance the environment with git-specific settings
        if isgitcmd:
            gitenv = getgitcmdenv()
            cmdenv.update(gitenv)
        
        if interactive:
            # run interactive commands directly
            # Determine working directory - use git root for git commands if available
            workdir = getreporoot() if isgitcmd else os.getcwd()
            
            result = runsubprocess(
                cmd, 
                check=True, 
                cwd=workdir, 
                capture_output=False,
                env=cmdenv
            )
                
            return result

        # progressbar and loading animation
        if withprogress:
            with tqdm(
                total=100,
                desc=f"{Fore.CYAN}  mrrping...{Style.RESET_ALL}",
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}',
                position=0,
                leave=False
            ) as innerpbar:
                # initial progress indication
                innerpbar.n = 20
                animation = startloadinganimation()
                
                # run command with optimized capture settings
                # Determine working directory - use git root for git commands if available
                workdir = getreporoot() if isgitcmd else os.getcwd()
                
                result = runsubprocess(
                    cmd, 
                    check=True, 
                    cwd=workdir, 
                    stdout=PIPE if captureoutput else None,
                    stderr=PIPE if captureoutput else None,
                    env=cmdenv
                )
                
                # calculate command execution time
                # executiontime = time() - starttime
                
                # update command timing cache for future optimization
                # if isgitcmd:
                #     commandtimingcache[" ".join(cmd[0:2])] = executiontime
                
                # update progress based on command completion
                innerpbar.n = 70
                innerpbar.refresh()
                stoploadinganimation(threadinfo=animation)
                
                # process and display output (only if we captured output)
                if result and captureoutput and result.stdout:
                    printoutput(result=result, flags=flags, pbar=innerpbar, mainpbar=pbar)
                
                # complete progress display and close
                innerpbar.n = 100
                innerpbar.colour = 'green'
                innerpbar.refresh()
                innerpbar.close()
                
                if printsuccess:
                    success("    ✓ completed successfully", pbar=innerpbar)
                
                return result
        
        # standard execution without progress display
        # determine working directory - use git root for git commands if available
        workdir = getreporoot() if isgitcmd else os.getcwd()
        
        result = runsubprocess(
            cmd, 
            check=True, 
            cwd=workdir, 
            stdout=PIPE if captureoutput else None,
            stderr=PIPE if captureoutput else None,
            env=cmdenv
        )
        
        # process output (only if we captured output)
        if result and captureoutput and result.stdout:
            printoutput(result, flags, pbar, pbar)
        
        if printsuccess:
            success("    ✓ completed successfully", pbar=pbar)
        
        return result

    except CalledProcessError as e:
        # error handling
        error(f"\n❌ command failed with exit code {e.returncode}:", pbar)
        printcmd(f"  $ {cmdstr}", pbar)
        
        # process error output
        outstr = e.stdout.decode('utf-8', errors='replace') if e.stdout else ""
        errstr = e.stderr.decode('utf-8', errors='replace') if e.stderr else ""
        
        if outstr:
            info(f"{Fore.BLACK}{outstr}", pbar)
        if errstr:
            error(f"{Fore.RED}{errstr}", pbar)
            suggestion = suggestfix(errstr)
            if suggestion:
                error(suggestion, pbar)
        
        # exit or continue based on flags
        if not flags.cont:
            exit(e.returncode)
        else:
            info(f"{Fore.CYAN}continuing despite error...", pbar)
        
        return None

    except KeyboardInterrupt:
        error("user interrupted", pbar)
        return None