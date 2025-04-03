from sys import stdout
from time import sleep, time
from colorama import Fore, Style # type: ignore
from threading import Event, Thread
from typing import List, Tuple, TypeAlias

'''
loading animations
'''

ThreadEventTuple: TypeAlias = Tuple[Thread, Event]
FrameType: TypeAlias = List[str]

def loadingthread(
        message: str, 
        stopevent: Event
        ) -> None:
    '''animated loading icon function to run in a thread'''
    frames: FrameType = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    frame: int = 0
    fmtmessage: str = f"{Fore.CYAN}{message}{Style.RESET_ALL}"
    
    while not stopevent.is_set():
        stdout.write(f'\r{frames[frame]} {fmtmessage}')
        stdout.flush()
        sleep(0.2)
        frame = (frame + 1) % len(frames) 
    
    # clear the line
    stdout.write(f'\r {len(fmtmessage)*2}\r')
    stdout.flush()

def startloadinganimation(message: str = "") -> ThreadEventTuple:
    '''start loading animation in a thread'''
    stop: Event = Event()
    anithread: Thread = Thread(
        target=loadingthread,
        args=(message, stop),
        daemon=True
    )
    anithread.start()
    return anithread, stop

def stoploadinganimation(threadinfo: ThreadEventTuple) -> None:
    '''stop threaded loading animation'''
    thread: Thread
    event: Event
    thread, event = threadinfo
    event.set()
    thread.join(timeout=0.2)  # wait for the thread to finish!!!!
    stdout.write('\r\x1b[2K\r') # use ansi codes to write the entire line to prevent artifacts
    stdout.flush()

def unthreadedloadinganimation(
        message: str, 
        duration: float = 2.0
        ) -> None:
    '''unthreaded loading animation'''
    frames: FrameType = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    frame: int = 0
    formattedmessage: str = f"{Fore.CYAN}{message}{Style.RESET_ALL}"
    endtime: float = time() + duration
    
    while time() < endtime:
        stdout.write(f'\r{frames[frame]} {formattedmessage}')
        stdout.flush()
        sleep(0.1)
        frame = (frame + 1) % len(frames)
    
    # clear the line
    stdout.write('\r\x1b[2K\r')
    stdout.flush()