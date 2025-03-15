from sys import exit
from os import getcwd
from time import time
from tqdm import tqdm # type: ignore
from argparse import Namespace
from colorama import Fore, Style # type: ignore
from typing import List, Optional, Dict
from subprocess import run as runsubprocess, CompletedProcess, CalledProcessError, PIPE

from utils.helpers import suggestfix, list2cmdline # type: ignore
from utils.loaders import startloadinganimation, stoploadinganimation # type: ignore
from utils.loggers import error, info, printcmd, printoutput, success, spacer # type: ignore

# cache for storing command execution times
# commandtimingcache: Dict[str, float] = {}

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

    # print command for dry run
    if flags.dry:
        printcmd(list2cmdline(cmd), pbar)
        return None

    # base command string for logging/caching
    cmdstr = list2cmdline(cmd)
    
    # for git commands, check command timing cache to optimize progress display
    isgitcmd = len(cmd) > 1 and cmd[0] == "git"
    # estimatedtime = commandtimingcache.get(cmdstr.split()[0:2], 1.0) if isgitcmd else 1.0

    try:
        spacer(pbar=pbar)
        info("    running command:", pbar)
        printcmd(f"      $ {cmdstr}", pbar)

        # determine if command should be interactive
        interactive = False
        if isinteractive is not None:
            interactive = isinteractive
        elif isgitcmd and len(cmd) >= 2:
            # git commit with no args is interactive
            if cmd[1] == "commit" and len(cmd) == 2:
                interactive = True

        # enhanced environment variables
        cmdenv = env or {}
        
        # start timing for performance tracking
        starttime = time()
        
        if interactive:
            # run interactive commands directly
            result = runsubprocess(
                cmd, 
                check=True, 
                cwd=getcwd(), 
                capture_output=False,
                env=cmdenv
            )
            
            # update command timing cache
            # if isgitcmd:
            #     commandtimingcache[" ".join(cmd[0:2])] = time() - starttime
                
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
                result = runsubprocess(
                    cmd, 
                    check=True, 
                    cwd=getcwd(), 
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
                
                # complete progress display
                innerpbar.n = 100
                innerpbar.colour = 'green'
                innerpbar.refresh()
                
                if printsuccess:
                    success("    ✓ completed successfully", pbar=innerpbar)
                
                return result
        
        # standard execution without progress display
        result = runsubprocess(
            cmd, 
            check=True, 
            cwd=getcwd(), 
            stdout=PIPE if captureoutput else None,
            stderr=PIPE if captureoutput else None,
            env=cmdenv
        )
        
        # update command timing cache
        # if isgitcmd:
        #     commandtimingcache[" ".join(cmd[0:2])] = time() - starttime
        
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