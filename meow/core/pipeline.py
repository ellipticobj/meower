from os import path, makedirs
from time import time
from tqdm import tqdm # type: ignore
from argparse import Namespace
from collections.abc import Callable
from typing import List, Optional, Dict, Tuple, Union, Any

from meow.core.executor import runcmd

from meow.utils.loggers import info

'''pipeline related functions'''

class PipelineStep:
    '''one step in the pipeline'''
    def __init__(
        self, 
        name: str, 
        func: Callable[[Namespace], Any], 
        noprogressbar: bool = False
    ):
        self.name = name
        self.func = func
        self.noprogressbar = noprogressbar

    def execute(
        self, 
        args: Namespace, 
        pbar: Optional[tqdm]
    ) -> Tuple[dict[str, Union[object,Any]], int]:
        '''executes the step'''
        start = time()
        toadd, cmd = self.func(args)

        result = runcmd(
            cmd=cmd,
            flags=args,
            pbar=pbar,
            withprogress=not self.noprogressbar
        )

        duration = time() - start
        report = {
            "step": self.name,
            "command": " ".join(cmd) if cmd else "",
            "duration": duration,
            "output": result.stdout.decode("utf-8", errors="replace") if result else "",
            "returncode": result.returncode if result else ""
        }
        return report, toadd


class Pipeline:
    def __init__(self, args: Namespace, steps: List[PipelineStep], pbar: tqdm):
        self.args = args
        self.steps = steps
        self.pbar = pbar
        self.report: List[Dict[str, Union[object, Any]]] = []

    def run(self) -> None:
        '''runs all steps in the pipeline'''
        starttime = time()
        for step in self.steps:
            reportitem: Dict[str, Union[object, Any]]
            toadd: Any
            reportitem, toadd = step.execute(self.args, self.pbar)
            
            # update bar
            if self.pbar.n < self.pbar.total:
                self.pbar.update(toadd)
            self.report.append(reportitem)

        totaltime = time() - starttime
        self.report.append({"step": "TOTAL", "duration": totaltime})
        
        # complete bar - ensure it's set to 100%
        if self.pbar and self.pbar.n < self.pbar.total:
            self.pbar.n = self.pbar.total - 1  # set to just before completion
            self.pbar.update(1)  # update to ensure proper rendering
            self.pbar.colour = 'green'
            self.pbar.refresh()  # make sure display is updated

    def generatereport(self, saveto: Optional[str] = None, pbar: Optional[tqdm] = None) -> None:
        '''generates report and saves to saveto if saveto is provided'''
        from datetime import datetime
        
        # get current timestamp
        timestamp: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # build report header
        output: List[str] = [
            "# meow execution report\n",
            f"generated: {timestamp}\n\n",
            "## summary\n",
            f"total steps: {len(self.report)-1}\n",  # -1 because last item is the TOTAL
            f"total duration: {self.report[-1]['duration']:.3f} seconds\n\n",
            "## steps\n\n"
        ]
        
        # add detailed step information
        for i, step in enumerate(self.report[:-1], 1):  # skip the TOTAL summary at the end
            cmd: str = str(step.get('command', 'N/A'))
            stepname: str = str(step['step'])
            duration = step['duration']
            returncode = step.get('returncode', 'N/A')
            
            # format step header
            output.append(f"### step {i}: {stepname}\n")
            output.append(f"command: `{cmd}`\n")
            output.append(f"duration: {duration:.3f} seconds\n")
            output.append(f"status: {'✓ success' if returncode == 0.0 else '❌ failed'}\n")
            
            # add step output if available (format for readability)
            if step.get("output"):
                # limit output length for readability
                outputtxt = str(step.get("output", ""))
                if len(outputtxt) > 500:
                    outputtxt = outputtxt[:500] + "...\n[output truncated]"
                
                output.append("\n```\n")
                output.append(outputtxt)
                output.append("\n```\n")
            
            output.append("\n")
        
        # add performance summary
        output.append("## performance summary\n\n")
        
        # sort steps by duration to find slowest steps
        sortedduration: List[Dict[str, Union[object, Any]]] = sorted(
            [step for step in self.report if step['step'] != 'TOTAL'],
            key=lambda x: x['duration'], # type: ignore
            reverse=True
        )
        
        if sortedduration:
            output.append("longest steps:\n")
            for i, step in enumerate(sortedduration[:3], 1):
                output.append(f"{i}. {step['step']}: {step['duration']:.3f}s\n")
            output.append("\n")
        
        output.append(f"total execution time: {self.report[-1]['duration']:.3f} seconds\n")

        # save or display report
        if saveto:
            # ensure directory exists
            reportdir = path.dirname(saveto)
            if reportdir and not path.exists(reportdir):
                makedirs(reportdir, exist_ok=True)
                
            # write report with proper formatting
            with open(saveto, 'w') as f:
                f.writelines(output)
            info(message="  i report generated", pbar=pbar)
        else:
            # display report to console
            for line in output:
                info(line, pbar=pbar)