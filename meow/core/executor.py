from sys import exit
import os
from time import time
from tqdm import tqdm # type: ignore
from argparse import Namespace
from colorama import Fore, Style # type: ignore
from typing import List, Optional, Dict
from subprocess import run as runsubprocess, CompletedProcess, CalledProcessError, PIPE

from meow.utils.helpers import suggestfix, list2cmdline # type: ignore
from meow.utils.loaders import startloadinganimation, stoploadinganimation # type: ignore
from meow.utils.loggers import error, info, printcmd, printoutput, success, spacer # type: ignore
from meow.utils.gitutils import getreporoot, getgitcmdenv, rungitcmd # type: ignore

# cache for storing command execution times
# commandtimingcache: Dict[str, float] = {}

def run_optimized_git_command(
    cmd: List[str],
    flags: Optional[Namespace] = None,
    pbar: Optional[tqdm] = None,
    withprogress: bool = True,
    captureoutput: bool = True
) -> Optional[CompletedProcess]:
    '''
    Optimized function to run git commands using GitPython when available
    
    Uses the GitRunner class which is more reliable for git credential handling
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

            returncode: int
            stdout: str
            stderr: str
            
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
    
    cmd: command to execute
    flags: optional flags controlling execution
    pbar: optional progress bar
    withprogress: show progress animation
    captureoutput: capture command output
    printsuccess: print success message
    isinteractive: interactive mode
    env: environment variables for the command
    '''
    # default flags
    flags = flags or Namespace(dry=False, cont=False, verbose=False)

    if not cmd:
        return None
        
    if len(cmd) > 1 and cmd[0] == "git" and not isinteractive:
        return run_optimized_git_command(
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
    # estimatedtime = commandtimingcache.get(cmdstr.split()[0:2], 1.0) if isgitcmd else 1.0

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
            git_env = getgitcmdenv()
            cmdenv.update(git_env)
        
        if interactive:
            # run interactive commands directly
            # Determine working directory - use git root for git commands if available
            work_dir = getreporoot() if isgitcmd else os.getcwd()
            
            result = runsubprocess(
                cmd, 
                check=True, 
                cwd=work_dir, 
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
                work_dir = getreporoot() if isgitcmd else os.getcwd()
                
                result = runsubprocess(
                    cmd, 
                    check=True, 
                    cwd=work_dir, 
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
        work_dir = getreporoot() if isgitcmd else os.getcwd()
        
        result = runsubprocess(
            cmd, 
            check=True, 
            cwd=work_dir, 
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