'''
git utilities for meower, written with help from anthropic's claude
'''
from git import Repo, GitCommandError, NoSuchPathError, InvalidGitRepositoryError
from os import path, getcwd, environ, chdir, getuid
from typing import List, Optional, Dict, Tuple, Union
from subprocess import run as runsubprocess, PIPE, CalledProcessError

def getreporoot() -> Optional[str]:
    '''get the git repository root directory'''
    try:
        result = runsubprocess(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
            stdout=PIPE,
            stderr=PIPE,
            cwd=getcwd()
        )
        rootpath = result.stdout.decode('utf-8').strip()
        
        if path.exists(rootpath):
            return rootpath
        return None
    except (CalledProcessError, FileNotFoundError):
        return None

class GitRunner:
    def __init__(self):
        self.repo = None
        try:
            gitroot = getreporoot()
            if gitroot:
                self.repo = Repo(gitroot)
        except (InvalidGitRepositoryError, NoSuchPathError):
            pass
    
    def run(self, cmd: List[str], env: Optional[Dict[str, str]] = None) -> Tuple[int, str, str]:
        """
        runs a git command and return (returncode, stdout, stderr)
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
            except GitCommandError as e:
                statuscode: Union[str, int, Exception, None] = e.status
                if not isinstance(statuscode, int):
                    statuscode = 1
                return statuscode, e.stdout, e.stderr
        
        try:
            gitcmd = ["git"] + cmd
            result = runsubprocess(
                gitcmd,
                check=False,
                cwd=getreporoot() or getcwd(),
                stdout=PIPE,
                stderr=PIPE,
                env=env or environ.copy()
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
        originaldir = getcwd()
        gitroot = getreporoot()
        
        if gitroot:
            chdir(gitroot)
        
        try:
            return func(*args, **kwargs)
        finally:
            # restore original directory
            chdir(originaldir)
    
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
    env = environ.copy()
    
    # ensure git has access to the global config
    if 'HOME' in env:
        gitconfigpath = path.join(env['HOME'], '.gitconfig')
        if path.exists(gitconfigpath):
            # make sure git can find global config
            env['GIT_CONFIG_GLOBAL'] = gitconfigpath
        
        # ensure XDG config is found if it exists
        xdgconfigpath = path.join(env['HOME'], '.config/git/config')
        if path.exists(xdgconfigpath):
            env['XDG_CONFIG_HOME'] = path.join(env['HOME'], '.config')
    
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
    if 'SSH_AUTH_SOCK' not in env and path.exists('/run/user'):
        # try to find SSH agent socket for git operations that need authentication
        uid = getuid()
        sshsock = f'/run/user/{uid}/keyring/ssh'
        if path.exists(sshsock):
            env['SSH_AUTH_SOCK'] = sshsock
    
    return env