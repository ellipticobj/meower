from sys import stdout
from time import sleep, time
from colorama import Fore, Style # type: ignore
from threading import Event, Thread
from typing import List, Tuple, TypeAlias, Any

'''
loading animations
'''

ThreadEventTuple: TypeAlias = Tuple[Thread, Event]
FrameType: TypeAlias = List[str]

def loadingthread(
        message: str, 
        stopevent: Event,
        pbar: Any = None
        ) -> None:
    '''animated loading icon function to run in a thread'''
    frames: FrameType = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    frame: int = 0
    fmtmessage: str = f"{Fore.CYAN}{message}{Style.RESET_ALL}"
    
    # if progress bar is provided, use its write method instead of stdout
    if pbar:
        while not stopevent.is_set():
            # avoid directly writing to stdout when a progress bar exists
            pbar.set_description(f"{Fore.CYAN}{frames[frame]} mrrping...{Style.RESET_ALL}")
            pbar.refresh()
            sleep(0.2)
            frame = (frame + 1) % len(frames)
    else:
        # original behavior for when no progress bar is provided
        while not stopevent.is_set():
            stdout.write(f'\r{frames[frame]} {fmtmessage}')
            stdout.flush()
            sleep(0.2)
            frame = (frame + 1) % len(frames) 
    
    # clear the line only if no progress bar was provided
    if not pbar:
        stdout.write(f'\r {len(fmtmessage)*2}\r')
        stdout.flush()

def startloadinganimation(message: str = "", pbar: Any = None) -> ThreadEventTuple:
    '''start loading animation in a thread'''
    stop: Event = Event()
    anithread: Thread = Thread(
        target=loadingthread,
        args=(message, stop, pbar),
        daemon=True
    )
    anithread.start()
    return anithread, stop

def stoploadinganimation(threadinfo: ThreadEventTuple) -> None:
    '''stop threaded loading animation'''
    thread: Thread
    event: Event
    thread, event = threadinfo
    
    # signal the thread to stop
    event.set()
    
    # wait for the thread to finish with timeout
    thread.join(timeout=0.2)

def unthreadedloadinganimation(
        message: str, 
        duration: float = 2.0,
        pbar: Any = None
        ) -> None:
    '''unthreaded loading animation'''
    frames: FrameType = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    frame: int = 0
    formattedmessage: str = f"{Fore.CYAN}{message}{Style.RESET_ALL}"
    endtime: float = time() + duration
    
    # if we have a progress bar, use it instead of direct stdout
    if pbar:
        while time() < endtime:
            pbar.set_description(f"{Fore.CYAN}{frames[frame]} mrrping...{Style.RESET_ALL}")
            pbar.refresh()
            sleep(0.1)
            frame = (frame + 1) % len(frames)
    else:
        # original direct stdout behavior
        while time() < endtime:
            stdout.write(f'\r{frames[frame]} {formattedmessage}')
            stdout.flush()
            sleep(0.1)
            frame = (frame + 1) % len(frames)
        # only clear the line if no progress bar was used
        stdout.write('\r\x1b[2K\r')
        stdout.flush()