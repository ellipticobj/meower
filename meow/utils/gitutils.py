'''
git utilities for meower, written with help from anthropic's claude
'''
import os
from typing import List, Optional, Dict, Tuple, Union
from subprocess import run as runsubprocess, PIPE, CalledProcessError
import git

def getreporoot() -> Optional[str]:
    '''get the git repository root directory'''
    try:
        result = runsubprocess(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
            stdout=PIPE,
            stderr=PIPE,
            cwd=os.getcwd()
        )
        rootpath = result.stdout.decode('utf-8').strip()
        
        if os.path.exists(rootpath):
            return rootpath
        return None
    except (CalledProcessError, FileNotFoundError):
        return None

class GitRunner:
    """
    provides a unified interface for git operations,
    falling back to subprocess if GitPython throws an error.
    """
    
    def __init__(self):
        self.repo = None
        try:
            gitroot = getreporoot()
            if gitroot:
                self.repo = git.Repo(gitroot)
        except (git.InvalidGitRepositoryError, git.NoSuchPathError):
            pass
    
    def run(self, cmd: List[str], env: Optional[Dict[str, str]] = None) -> Tuple[int, str, str]:
        """
        runs a git command and return (returncode, stdout, stderr)
        cmd: Git command as a list of strings (without 'git' prefix)
        env: Environment variables for the command
            
        returns tuple of (returncode, stdout, stderr)
        """
        if self.repo:
            try:
                gitcmd = self.repo.git
                
                if env:
                    # only set environment variables that are safe to set as attributes
                    gitenv = {}
                    for key, value in env.items():
                        # use environment dict instead of trying to set attributes
                        gitenv[f"GIT_{key}"] = value
                    
                    # set the environment dictionary instead of individual attributes
                    gitcmd.update_environment(**gitenv)
                
                output = gitcmd.execute(cmd)
                return 0, output, ""
            except git.GitCommandError as e:
                statuscode: Union[str, int, Exception, None] = e.status
                if not isinstance(statuscode, int):
                    statuscode = 1
                return statuscode, e.stdout, e.stderr
        
        try:
            gitcmd = ["git"] + cmd
            result = runsubprocess(
                gitcmd,
                check=False,
                cwd=getreporoot() or os.getcwd(),
                stdout=PIPE,
                stderr=PIPE,
                env=env or os.environ.copy()
            )
            return (
                result.returncode,
                result.stdout.decode('utf-8', errors='replace'),
                result.stderr.decode('utf-8', errors='replace')
            )
        except Exception as e:
            return 1, "", str(e)

def ensuregitdir(func):
    '''decorator to ensure git commands run from the repository root'''
    def wrapper(*args, **kwargs):
        originaldir = os.getcwd()
        gitroot = getreporoot()
        
        if gitroot:
            os.chdir(gitroot)
        
        try:
            return func(*args, **kwargs)
        finally:
            # restore original directory
            os.chdir(originaldir)
    
    return wrapper

def isgitrepo() -> bool:
    '''check if current directory is in a git repository'''
    return getreporoot() is not None

# global gitrunner instance for reuse
_gitrunner = None

def getgitrunner() -> GitRunner:
    '''gets a gitrunner instance (creates one if it doesn't exist)'''
    global _gitrunner
    if _gitrunner is None:
        _gitrunner = GitRunner()
    return _gitrunner

def rungitcmd(cmd: List[str], env: Optional[Dict[str, str]] = None) -> Tuple[int, str, str]:
    '''runs a git command using gitrunner'''
    runner = getgitrunner()
    if cmd[0] != "git":
        cmd = ["git"] + cmd
    return runner.run(cmd, env or getgitcmdenv())

def getgitcmdenv() -> Dict[str, str]:
    '''gets environment variables for git commands'''
    env = os.environ.copy()
    
    # ensure git has access to the global config
    if 'HOME' in env:
        gitconfigpath = os.path.join(env['HOME'], '.gitconfig')
        if os.path.exists(gitconfigpath):
            # make sure git can find global config
            env['GIT_CONFIG_GLOBAL'] = gitconfigpath
        
        # ensure XDG config is found if it exists
        xdgconfigpath = os.path.join(env['HOME'], '.config/git/config')
        if os.path.exists(xdgconfigpath):
            env['XDG_CONFIG_HOME'] = os.path.join(env['HOME'], '.config')
    
    try:
        # get user.name from git config
        username = runsubprocess(
            ["git", "config", "--get", "user.name"],
            check=False, stdout=PIPE, stderr=PIPE
        )
        if username.returncode == 0:
            env['GIT_AUTHOR_NAME'] = username.stdout.decode('utf-8').strip()
            env['GIT_COMMITTER_NAME'] = env['GIT_AUTHOR_NAME']
        
        # get user.email from git config
        useremail = runsubprocess(
            ["git", "config", "--get", "user.email"],
            check=False, stdout=PIPE, stderr=PIPE
        )
        if useremail.returncode == 0:
            env['GIT_AUTHOR_EMAIL'] = useremail.stdout.decode('utf-8').strip()
            env['GIT_COMMITTER_EMAIL'] = env['GIT_AUTHOR_EMAIL']
    except Exception:
        # if we can't get the config, continue without these values
        pass
    
    # for SSH operations
    if 'SSH_AUTH_SOCK' not in env and os.path.exists('/run/user'):
        # try to find SSH agent socket for git operations that need authentication
        uid = os.getuid()
        sshsock = f'/run/user/{uid}/keyring/ssh'
        if os.path.exists(sshsock):
            env['SSH_AUTH_SOCK'] = sshsock
    
    return env