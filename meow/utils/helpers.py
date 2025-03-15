import sys
from os import getcwd
from config import VERSION # type: ignore
from typing import List, Tuple
from colorama import Fore, Style # type: ignore
from argparse import ArgumentParser, _ArgumentGroup, Namespace

from utils.loggers import error, info, spacer # type: ignore

def initcommands(parser: ArgumentParser) -> None:
    '''initialize commands with commands.'''
    # core functionality
    parser.add_argument("message", nargs='*', help="commit message (overrides --no-message)")
    parser.add_argument("-a", "--add", dest="add", nargs="+", help="select specific files to stage")

    # general options
    generalgrp: _ArgumentGroup = parser.add_argument_group("general options")
    generalgrp.add_argument("-v", "--version", action='store_true', help="show version")
    generalgrp.add_argument("-c", "--continue", dest="cont", action='store_true', help="continue after errors")
    generalgrp.add_argument("-q", "--quiet", action='store_true', help="suppress output")
    generalgrp.add_argument("-ve", "--verbose", action='store_true', help="verbose output")
    generalgrp.add_argument("--dry", dest = "dry", action='store_true', help="preview commands without execution")
    generalgrp.add_argument("--status", action='store_true', help="show git status before executing commands")

    # commit options
    commitgrp: _ArgumentGroup = parser.add_argument_group("commit options")
    commitgrp.add_argument("-n", "--no-message", dest="nomsg", action='store_true', help="allow empty commit message")
    commitgrp.add_argument("--allow-empty", dest="allowempty", action='store_true', help="allow empty commit")
    commitgrp.add_argument("--diff", action='store_true', help="show diff before committing")
    commitgrp.add_argument("--amend", action='store_true', help="amend previous commit")

    # push options
    pushgrp: _ArgumentGroup = parser.add_argument_group("push options")
    pushgrp.add_argument("-u", "--upstream", "--set-upstream", nargs='+', metavar="REMOTE/BRANCH", help="set upstream branch to push to (formats: REMOTE BRANCH or REMOTE/BRANCH)")
    pushgrp.add_argument("-f", "--force", action='store_true', help="force push")
    pushgrp.add_argument("-np", "--no-push", dest="nopush", action='store_true', help="skip pushing")
    pushgrp.add_argument("--tags", action='store_true', help="push tags with commits")

    # pull options
    pullgrp: _ArgumentGroup = parser.add_argument_group("pull options")
    pullgrp.add_argument("--pull", action='store_true', help="run git pull before pushing")
    pullgrp.add_argument("--pull-no-rebase", dest="norebase", action='store_true', help="run git pull --no-rebase (overrides --pull)")

    # advanced options
    advancedgrp: _ArgumentGroup = parser.add_argument_group("advanced options")
    advancedgrp.add_argument("--update-submodules", dest="updatesubmodules", action='store_true', help="update submodules recursively")
    advancedgrp.add_argument("--stash", action='store_true', help="stash changes before pull")
    advancedgrp.add_argument("--report", action='store_true', help="generate and output a report after everything is run") # TODO: add option to save to file, and to specify filename


def validateargs(args: Namespace) -> None:
    '''validate argument comb'''
    if not args.amend and not args.nomsg and not args.message:
        error("commit message required (use --amend, --no-message, or provide message)")
        sys.exit(1)

def getpipelinesteps(args: Namespace) -> List:
    '''get pipeline steps'''
    from core.pipeline import PipelineStep # type: ignore
    steps: List[PipelineStep] = []

    def getstatus(args: Namespace):
        return (1, ["git", "status"]) if args.status else (0, [])
    
    def updatesubmodules(args: Namespace):
        return (1, ["git", "submodule", "update", "--init", "--recursive"]) if args.updatesubmodules else (0, [])
    
    def getstash(args: Namespace):
        return (1, ["git", "stash"]) if args.stash else (0, [])
    
    def getpull(args: Namespace):
        return (1, ["git", "pull"]) if args.pull or args.norebase else (0, [])
    
    def getstage(args: Namespace):
        return (1, ["git", "add", *args.add] if args.add else ["git", "add", "."])
    
    def getdiff(args: Namespace):
        return (1, ["git", "diff", "--staged"]) if args.diff else (0, [])
    
    def getcommit(args: Namespace):
        return (1, _getcommitcommand(args))
    
    def getpush(args: Namespace):
        return (1, _getpushcommand(args)) if not args.nopush else (0, [])

    # create steps
    steps = [
        PipelineStep("get status", getstatus, noprogressbar=True),
        PipelineStep("update submodules", updatesubmodules),
        PipelineStep("stash changes", getstash),
        PipelineStep("pull from remote", getpull),
        PipelineStep("stage changes", getstage),
        PipelineStep("get diff", getdiff, noprogressbar=True),
        PipelineStep("commit changes", getcommit),
        PipelineStep("push changes", getpush)
    ]

    return [step for step in steps if step.func(args)[0] > 0]

def _getcommitcommand(args: Namespace) -> List[str]:
    '''generate commit command'''
    commitcmd = ["git", "commit"]
    
    if args.message:
        message = " ".join(args.message) if isinstance(args.message, list) else args.message
        commitcmd.extend(["-m", message])
    elif args.nomsg:
        commitcmd.append("--allow-empty-message")
    
    if args.amend:
        commitcmd.append("--amend")
    
    if args.allowempty:
        commitcmd.append("--allow-empty")
    
    if args.quiet:
        commitcmd.append("--quiet")
    elif args.verbose:
        commitcmd.append("--verbose")
    
    return commitcmd

def _getpushcommand(args: Namespace) -> List[str]:
    '''generate push commands'''
    pushcmd = ["git", "push"]
    
    if args.tags:
        pushcmd.append("--tags")
    
    if args.upstream:
        pushcmd = _parseupstreamargs(args, pushcmd)
    
    if args.force:
        pushcmd.append("--force-with-lease")
    
    if args.quiet:
        pushcmd.append("--quiet")
    elif args.verbose:
        pushcmd.append("--verbose")
    
    return pushcmd

def _parseupstreamargs(args: Namespace, pushcmd: List[str]) -> List[str]:
    '''parse --set-upstream args'''
    remote: str
    branch: str
    
    if len(args.upstream) == 1 and '/' in args.upstream[0]:
        remote, branch = args.upstream[0].split('/')
        pushcmd.extend(["--set-upstream", remote, branch])
    elif len(args.upstream) == 2:
        pushcmd.extend(["--set-upstream", args.upstream[0], args.upstream[1]])
    else:
        error("invalid upstream format. use 'remote branch' or 'remote/branch'")
        sys.exit(1)
    
    return pushcmd

def getgitcommands(
    gitcommand: str,
    commandargs: List[str]
) -> Tuple[List[str], List[str]]:
    '''get commands based on input'''
    # commands that automatically add before executing
    autoaddcommands = {"commit", "amend"}
    
    # commands with special flags handling
    if gitcommand == "add":
        return [], ["git", "add"] + (commandargs or ["."])
    elif gitcommand == "commit":
        # check if `-m` is part of arguments as standalone or part of another arg
        hasmsg = any(arg == "-m" for arg in commandargs) or any(arg.startswith("-m") for arg in commandargs)
        
        if hasmsg:
            return ["git", "add", "."], ["git", "commit"] + commandargs
        elif commandargs:
            # if arguments exist but no explicit message, treat args as message
            return ["git", "add", "."], ["git", "commit", "-m"] + commandargs
        else:
            # no args, allow empty message for interactive commit
            return ["git", "add", "."], ["git", "commit", "--allow-empty-message"]
    elif gitcommand == "pull":
        # add --autostash by default unless explicitly disabled
        if "--no-autostash" not in commandargs:
            commandargs = commandargs + ["--autostash"]
        return [], ["git", "pull"] + commandargs
    elif gitcommand == "clone":
        # add helpful defaults unless explicitly overridden
        if not any(arg in commandargs for arg in ["--quiet", "-q"]):
            if "--verbose" not in commandargs and "-v" not in commandargs:
                commandargs.append("--verbose")
        if not any(arg in commandargs for arg in ["--no-recursive"]):
            if "--recursive" not in commandargs:
                commandargs.append("--recursive")
        if "--remote-submodules" not in commandargs:
            commandargs.append("--remote-submodules")
        return [], ["git", "clone"] + commandargs
    elif gitcommand == "push":
        # handle common push options
        if "--tags" not in commandargs and not any(arg == "--follow-tags" for arg in commandargs):
            # don't add if explicitly set to --no-tags````````````                                      
            if "--no-tags" not in commandargs:
                commandargs.append("--follow-tags")
        return [], ["git", "push"] + commandargs
    elif gitcommand == "checkout" or gitcommand == "switch":
        # create branch if it doesn't exist (common use case)
        if "-b" not in commandargs and "--branch" not in commandargs and "-c" not in commandargs and "--create" not in commandargs:
            if len(commandargs) > 0 and not commandargs[0].startswith("-"):
                # add -b only if first arg looks like a branch name and -b isn't already specified
                if not any(arg.startswith("-") for arg in commandargs):
                    return [], ["git", gitcommand, "-b"] + commandargs
        return [], ["git", gitcommand] + commandargs
    elif gitcommand in autoaddcommands:
        # auto stage changes for certain commands
        return ["git", "add", "."], ["git", gitcommand] + commandargs
    else:
        # default handling for all other git commands
        return [], ["git", gitcommand] + commandargs

def displayheader() -> None:
    '''displays program header'''
    info(f"{Fore.MAGENTA}{Style.BRIGHT}meow {Style.RESET_ALL}{Fore.CYAN}v{VERSION}{Style.RESET_ALL}")
    info(f"\ncurrent directory: {Style.BRIGHT}{getcwd()}\n")

def displaysteps(steps: List) -> None:
    '''displays pipeline steps'''
    info(f"{Fore.CYAN}{Style.BRIGHT}meows to meow:{Style.RESET_ALL}")
    for i, step in enumerate(steps, 1):
        info(f"  {Fore.BLUE}{i}.{Style.RESET_ALL} {Fore.BLACK}{step.name}{Style.RESET_ALL}")
    spacer()

def suggestfix(errormsg: str) -> str:
    '''suggest fixes for common git errors'''
    # ai helped with this, i went through manually and tweaked some parts
    msg = errormsg.lower()
    feedback: List[str] = []
    
    # push/pull related errors
    if "non-fast-forward" in msg or "rejected" in msg:
        feedback.append("    f try running `git pull` before pushing, or use --force-with-lease")
    if "failed to push some refs" in msg:
        feedback.append("    f remote contains work you do not have locally. run `git fetch` then `git pull`")
    
    # authentication errors
    if "permission denied" in msg:
        feedback.append("    f do you have permissions?")
    if "authentication failed" in msg:
        feedback.append("    f verify your username and password/token are correct")
    if "could not read from remote repository" in msg:
        feedback.append("    f check repo url and your network connection")
    
    # merge/conflict errors
    if "merge conflict" in msg:
        feedback.append("    f resolve conflicts manually then commit the result")
    if "overwritten by merge" in msg:
        feedback.append("    f stash your changes first with `git stash`, then pull")
    if "your local changes to the following files would be overwritten by" in msg:
        feedback.append("    f stash or commit your changes before pulling")
    
    # branch related errors
    if "not a valid object name" in msg or "did not match any file(s) known to git" in msg:
        feedback.append("    f is your branch name correct?")
    if "a branch named" in msg and "already exists" in msg:
        feedback.append("    f use a different branch name")
    if "src refspec" in msg and "does not match any" in msg:
        feedback.append("    f branch does not exist... did you misspell something?")
    
    # commit related errors
    if "nothing to commit" in msg:
        feedback.append(f"    i {Fore.CYAN}nothing to commit")
    if "no changes added to commit" in msg:
        feedback.append("    f stage changes first with `git add` before committing")
    if "please tell me who you are" in msg:
        feedback.append("    f set your identity with: `git config --global user.email \"you@example.com\"` and `git config --global user.name \"Your Name\"`")
    
    # status msgs
    if "already up to date" in msg or "already up-to-date" in msg:
        feedback.append(f"    i {Fore.CYAN}everything up to date")
    
    # submodule errors
    if "could not resolve host" in msg:
        feedback.append("    f check your internet connection or repository URL")
    if "no submodule mapping found" in msg:
        feedback.append("    f initialize submodules with `git submodule init` first")
    
    # git config errors
    if "bad config file" in msg:
        feedback.append("    f check format of your git config file")
    
    # if no specific feedback, give general git info
    if not feedback and "fatal:" in msg:
        feedback.append("    f check `git help` or `git help <command>` for more information")
    
    return "\n".join(feedback)

def list2cmdline(cmd: List[str]) -> str:
    '''convert command list to string'''
    return " ".join(cmd)