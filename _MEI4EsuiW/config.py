from typing import Dict, Final

VERSION: Final[str] = "1.0.0-preview1"

GITCOMMANDMESSAGES: Dict[str, str] = {
    'log': 'q to exit: ',
    'add': 'staging...',
    'push': 'pushing...',
    'pull': 'pulling...',
    'clone': 'cloning...',
    'fetch': 'fetching...',
    'branch': 'branching...',
    'commit': 'committing...',
    'diff': 'showing diffs...',
    'status': 'checking repo status...'
}

KNOWNCOMMANDS: list[str] = list(GITCOMMANDMESSAGES.keys())