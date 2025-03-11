from typing import List, Dict
from sys import exit
from tqdm import tqdm # type: ignore
from colorama import Fore, Style # type: ignore
from core.executor import runcmd # type: ignore
from utils.loaders import startloadinganimation, stoploadinganimation # type: ignore
from utils.helpers import list2cmdline, getgitcommands # type: ignore
from utils.loggers import error # type: ignore

def handlegitcommands(args: List[str], messages: Dict[str, str]) -> None:
    gitcmd = args[1]
    commandargs = args[2:] if len(args) > 2 else []
    
    if gitcmd == "log":
        cmd = ["git", "log"] + commandargs
        result = runcmd(cmd, captureoutput=False)
        exit(result.returncode if result else 1)
    
    try:
        with tqdm(
            total=100,
            desc=f"{Fore.CYAN}meowing...{Style.RESET_ALL}",
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}',
            position=0,
            leave=True
        ) as mainpbar:
            mainpbar.update(10)
            
            loadingmsg = messages.get(gitcmd, "mrrping...")
            
            animation = startloadinganimation(loadingmsg)
            
            precmd, cmd = getgitcommands(gitcmd, commandargs)
            lastcmdstr = list2cmdline(cmd)
            
            if precmd:
                runcmd(precmd, pbar=mainpbar)
            
            result = runcmd(cmd, pbar=mainpbar)
            
            stoploadinganimation(animation)
            
            mainpbar.update(100)
            mainpbar.n = 100
            mainpbar.refresh()
            
            exit(0 if result and result.returncode == 0 else 1)
    
    except KeyboardInterrupt:
        error(f"{Fore.CYAN}user interrupted")
        exit(1)