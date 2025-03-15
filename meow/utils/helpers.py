import sys
import shlex
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
    if gitcommand == "add":
        return [], ["git", "add"] + (commandargs or ["."])
    elif gitcommand == "commit":
        if ["-m"] in commandargs:
            return ["git", "add", "."], ["git", "commit"] + commandargs
        elif commandargs:
            return ["git", "add", "."], ["git", "commit"] + ["-m"] + commandargs
        else:
            return ["git", "add", "."], ["git", "commit", "--allow-empty-message"]
    elif gitcommand == "pull":
        return [], ["git", "pull"] + commandargs + ["--autostash"]
    elif gitcommand == "clone":
        return [], ["git", "clone"] + commandargs + ["--verbose", "--recursive", "--remote-submodules"]
    else:
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

def suggestfix(error_msg: str) -> str:
    '''suggest fixes for common errors'''
    msg = error_msg.lower()
    feedback: List[str] = []
    
    if "non-fast-forward" in msg or "rejected" in msg:
        feedback.append("try running `git pull` before pushing, or use --force-with-lease")
    if "permission denied" in msg:
        feedback.append("check your ssh keys or credentials")
    if "Already up to date." in msg:
        feedback.append(f"    i {Fore.CYAN}everything up to date")
    if "nothing to commit" in msg:
        feedback.append(f"    i {Fore.CYAN}nothing to commit")
    
    return "\n".join(feedback)

def list2cmdline(cmd: List[str]) -> str:
    '''convert command list to string'''
    return " ".join(cmd)