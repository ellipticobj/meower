from typing import List, Dict
from sys import exit
from tqdm import tqdm # type: ignore
from colorama import Fore, Style # type: ignore
from meow.config import INTERACTIVECMDS, SPECIALSUBCOMMANDHANDLING
from meow.core.executor import runcmd
from meow.utils.loaders import startloadinganimation, stoploadinganimation
from meow.utils.helpers import list2cmdline, getgitcommands
from meow.utils.loggers import error

def handlegitcommands(args: List[str], messages: Dict[str, str]) -> None:
    """handle any git command through the meow wrapper"""
    gitcmd = args[1]
    commandargs = args[2:] if len(args) > 2 else []
    
    # handle interactive commands separately
    if gitcmd in INTERACTIVECMDS:
        try:
            with tqdm(
                total=100,
                desc=f"{Fore.CYAN}meowing...{Style.RESET_ALL}",
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}',
                position=0,
                leave=True
            ) as mainpbar:
                mainpbar.update(10)
                
                loadingmsg = messages.get(gitcmd, f"running git {gitcmd}...")
                animation = startloadinganimation(loadingmsg)
                
                cmd = ["git", gitcmd] + commandargs
                result = runcmd(cmd, captureoutput=False, isinteractive=True)
                
                stoploadinganimation(animation)
                mainpbar.update(100)
                mainpbar.refresh()
                
                from meow.utils.loggers import success
                success("    ✓ completed successfully")
                
                exit(result.returncode if result else 1)
        except KeyboardInterrupt:
            error("user interrupted")
            exit(1)
    
    try:
        with tqdm(
            total=100,
            desc=f"{Fore.CYAN}meowing...{Style.RESET_ALL}",
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}',
            position=0,
            leave=True
        ) as mainpbar:
            mainpbar.update(10)
            
            loadingmsg = messages.get(gitcmd, f"running git {gitcmd}...")
            
            animation = startloadinganimation(loadingmsg)
            
            # get the appropriate git commands
            precmd, cmd = getgitcommands(gitcmd, commandargs)
            lastcmdstr = list2cmdline(cmd)
            
            # run pre-command if needed
            if precmd:
                runcmd(precmd, pbar=mainpbar)
            
            # check for special subcommand handling
            isinteractive = determineifinteractive(gitcmd, commandargs)
            
            # run the main command
            result = runcmd(cmd, pbar=mainpbar, isinteractive=isinteractive)
            
            stoploadinganimation(animation)
            
            mainpbar.update(100)
            mainpbar.n = 100
            mainpbar.refresh()
            
            exit(0 if result and result.returncode == 0 else 1)
    
    except KeyboardInterrupt:
        error("user interrupted")
        exit(1)

def determineifinteractive(gitcmd: str, commandargs: List[str]) -> bool:
    """determine if a command should be run in interactive mode"""
    # base interactive commands
    if gitcmd in INTERACTIVECMDS:
        return True
    
    # commit with no message is interactive
    if gitcmd == "commit" and not any(arg.startswith("-m") for arg in commandargs) and "-m" not in commandargs:
        return True
    
    # check for special subcommands
    if gitcmd in SPECIALSUBCOMMANDHANDLING and commandargs:
        subcommand = commandargs[0].lstrip('-')
        if subcommand in SPECIALSUBCOMMANDHANDLING[gitcmd]:
            return True
    
    # check for editor-based commands
    if (gitcmd == "commit" and "--edit" in commandargs) or (gitcmd == "tag" and "-e" in commandargs):
        return True
    
    return False