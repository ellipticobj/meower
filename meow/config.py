from typing import Dict, Final, List

VERSION: Final[str] = "1.2.1"

# commands that should use captureoutput=False for interactive use
INTERACTIVECMDS = {
    "log", "add", "rebase", "bisect", "blame", 
    "cherry-pick", "mergetool", "difftool", "diff"
}

# commands that require special handling for certain subcommands
SPECIALSUBCOMMANDHANDLING = {
    "branch": [
        "delete", "move", "copy", "edit-description", 
        "set-upstream", "unset-upstream"
    ],
    "remote": [
        "add", "rename", "remove", "set-url", 
        "get-url", "show", "prune", "update"
    ],
    "config": [
        "get", "set", "unset", "list", "edit"
    ]
}

# ai generated because im not a git nerd
GITCOMMANDMESSAGES: Dict[str, str] = {
    # porcelain commands (common user-facing commands)
    'add': 'staging changes...',
    'am': 'applying patches...',
    'archive': 'creating archive...',
    'bisect': 'hunting for bugs...',
    'branch': 'managing branches...',
    'bundle': 'bundling refs...',
    'checkout': 'switching branches...',
    'cherry-pick': 'cherry-picking commits...',
    'clean': 'removing untracked files...',
    'clone': 'cloning repository...',
    'commit': 'committing changes...',
    'describe': 'finding nearest tag...',
    'diff': 'showing differences...',
    'fetch': 'fetching from remote...',
    'format-patch': 'creating patches...',
    'gc': 'cleaning up...',
    'grep': 'searching files...',
    'init': 'creating repository...',
    'log': 'displaying history...',
    'merge': 'merging branches...',
    'mv': 'moving files...',
    'notes': 'managing notes...',
    'pull': 'pulling changes...',
    'push': 'pushing changes...',
    'rebase': 'rebasing commits...',
    'reflog': 'managing reflog...',
    'remote': 'managing remotes...',
    'reset': 'resetting state...',
    'restore': 'restoring files...',
    'revert': 'reverting commits...',
    'rm': 'removing files...',
    'shortlog': 'summarizing history...',
    'show': 'showing objects...',
    'stash': 'stashing changes...',
    'status': 'checking status...',
    'submodule': 'managing submodules...',
    'switch': 'switching branches...',
    'tag': 'managing tags...',
    'worktree': 'managing worktrees...',
    
    # plumbing commands (low-level commands)
    'cat-file': 'examining objects...',
    'check-ignore': 'checking ignores...',
    'commit-tree': 'creating commit...',
    'count-objects': 'counting objects...',
    'diff-index': 'comparing index...',
    'diff-tree': 'comparing trees...',
    'hash-object': 'hashing content...',
    'ls-files': 'listing files...',
    'ls-tree': 'listing tree...',
    'merge-base': 'finding common ancestor...',
    'read-tree': 'reading tree...',
    'rev-list': 'listing revisions...',
    'rev-parse': 'parsing revisions...',
    'show-ref': 'showing refs...',
    'symbolic-ref': 'reading symbolic refs...',
    'update-index': 'updating index...',
    'update-ref': 'updating refs...',
    'verify-pack': 'verifying pack...',
    'write-tree': 'writing tree...',
    
    # additional common commands
    'blame': 'analyzing blame...',
    'config': 'configuring git...',
    'for-each-ref': 'iterating refs...',
    'help': 'showing help...',
    'rerere': 'reusing recorded resolutions...',
    'fsck': 'checking file system...',
    'maintenance': 'maintaining repo...',
    'prune': 'pruning objects...',
}

# list of all git commands (both listed above and any others)
KNOWNCOMMANDS: List[str] = list(GITCOMMANDMESSAGES.keys()) + [
    # additional git commands not in the message dictionary
    'annotate', 'apply', 'bugreport', 'check-attr', 'check-mailmap', 'check-ref-format', 
    'column', 'difftool', 'fast-export', 'fast-import', 'filter-branch', 'fmt-merge-msg',
    'interpret-trailers', 'mailinfo', 'mailsplit', 'merge-file', 'merge-index', 'mergetool',
    'mktag', 'mktree', 'multi-pack-index', 'pack-objects', 'pack-redundant', 'pack-refs',
    'patch-id', 'range-diff', 'receive-pack', 'replace', 'send-email', 'send-pack',
    'sparse-checkout', 'unpack-file', 'unpack-objects', 'var', 'verify-commit', 'whatchanged'
]