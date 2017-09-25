---
{
  "date": "2017-09-25",
  "subtitle": "How I learned to stop worrying and love the event loop",
  "title": "Wrapping Subprocesses in Asyncio"
}
---
<!--more-->

I once had a coworker tasked with creating a web-based dashboard. Unfortunately, the data he needed to log and visualize came from this binary application that didn't have any sort of documented developer api -- it just printed everything to stdout -- that he didn't have the source code for either. 

It was basically a black box that he had to write a Python wrapper around, using the [subprocess](https://docs.python.org/3/library/subprocess.html) module.

His wrapper basically worked as such:

1. Run the binary in a subprocess
2. Write an infinite loop that with each iteration attempts to... 
    - capture each new line as it's printed from the subprocess
    - marshal the line into some form of structured data i.e. dictionary
    - log the information in the data structure

## A Synchronous Example


```python
from subprocess import Popen, PIPE
import logging; logging.getLogger().setLevel(logging.INFO)
import sys
import time
import json


PROG = """
import json
import time
from datetime import datetime

while True:
    data = {
       'time': datetime.now().strftime('%c %f milliseconds'),
       'string': 'hello, world',
    }
    print(json.dumps(data))
"""

with Popen([sys.executable, '-u', '-c', PROG], stdout=PIPE) as proc:
    last_line = ''
    start_time, delta = time.time(), 0
    
    while delta < 5: # only loop for 5 seconds
        
        line = proc.stdout.readline().decode()
        
        # pretend marshalling the data takes 1 second
        data = json.loads(line); time.sleep(1)
        
        if line != last_line:
            logging.info(data)
        
        last_line = line
        delta = time.time() - start_time
```

    INFO:root:{'time': 'Mon Sep 25 16:16:21 2017 690000 milliseconds', 'string': 'hello, world'}
    INFO:root:{'time': 'Mon Sep 25 16:16:21 2017 690084 milliseconds', 'string': 'hello, world'}
    INFO:root:{'time': 'Mon Sep 25 16:16:21 2017 690111 milliseconds', 'string': 'hello, world'}
    INFO:root:{'time': 'Mon Sep 25 16:16:21 2017 690131 milliseconds', 'string': 'hello, world'}
    INFO:root:{'time': 'Mon Sep 25 16:16:21 2017 690149 milliseconds', 'string': 'hello, world'}


# The problem

The problem my coworker had is that in the time he marshaled one line of output of the program and logged the information, several more lines had already been printed by the subprocess. His wrapper simply couldn't keep up with the subprocess' output.

Notice in the example above, that although many more lines have obviously been printed from the program, we only capture the first few since our subprocess "reads" new lines more slowly than they're printed.

# The solution-  asyncio

Instead of writing our own infinite loop, what if we had a loop that would allow us to run a subprocess and intelligently poll it to determine when a new line was ready to be read, yielding to the main thread to do other work if not?

What if that same event loop allowed us to delegate the process of marshaling the json output to a ProcessPoolExecutor?

What if this event loop was written into the Python standard library? Well...

### printer.py 
This program simply prints random stuff to stdout on an infinite loop

```python
# printer.py 
#
# print to stdout in infinite loop

from datetime import datetime
from pathlib import Path
from time import sleep
from typing import List
import random
import json
import os


def get_words_from_os_dict() -> List[str]:
    p1 = Path('/usr/share/dict/words')  # mac os
    p2 = Path('/usr/dict/words')  # debian/ubuntu
    words: List[str] = []
    if p1.exists:
        words = p1.read_text().splitlines()
    elif p2.exists:
        words = p2.read_text().splitlines()
    return words


def current_time() -> str:
    return datetime.now().strftime("%c")


def printer(words: List[str] = get_words_from_os_dict()) -> str:
    random_words = ':'.join(random.choices(words, k=random.randrange(2, 5))) if words else 'no OS words file found'
    return json.dumps({
        'current_time': current_time(),
        'words': random_words
    })


while True:
    seconds = random.randrange(5)
    print(f'{__file__} in process {os.getpid()} waiting {seconds} seconds to print json string')
    sleep(seconds)
    print(printer())
```

# An Asynchronous Example

This program wraps printer.py in a subprocess. It then delegates the marshaling of json to another process using the event loop's [`run_in_executor`](https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.AbstractEventLoop.run_in_executor) method, and prints the results to the screen.


```python
#!/usr/bin/env python3
#
# Spawns multiple instances of printer.py and attempts to deserialize the output
# of each line in another process and print the result to the screen,
import typing as T
import asyncio.subprocess
import logging
import sys
import json

from concurrent.futures import ProcessPoolExecutor, Executor
from functools import partial
from contextlib import contextmanager


@contextmanager
def event_loop() -> asyncio.AbstractEventLoop:
    loop = asyncio.get_event_loop()
    # default asyncio event loop executor is
    # ThreadPoolExecutor which is usually fine for IO-bound
    # tasks, but bad if you need to do computation
    with ProcessPoolExecutor() as executor:
        loop.set_default_executor(executor)
        yield loop
    loop.close()
    print('\n\n---loop closed---\n\n')


# any `async def` function is a coroutine
async def read_json_from_subprocess(
        loop: asyncio.AbstractEventLoop = asyncio.get_event_loop(),
        executor: T.Optional[Executor] = None
) -> None:
    # wait for asyncio to initiate our subprocess
    process: asyncio.subprocess.Process = await create_process()

    while True:
        bytes_ = await process.stdout.readline()
        string = bytes_.decode('utf8')
        # deserialize_json is a function that
        # we'll send off to our executor
        deserialize_json = partial(json.loads, string)

        try:
            # run deserialize_json in the loop's default executor (ProcessPoolExecutor)
            # and wait for it to return
            output = await loop.run_in_executor(executor, deserialize_json)
            print(f'{process} -> {output}')
        except json.decoder.JSONDecodeError:
            logging.error('JSONDecodeError for input: ' + string.rstrip())


def create_process() -> asyncio.subprocess.Process:
    return asyncio.create_subprocess_exec(
        sys.executable, '-u', 'printer.py',
        stdout=asyncio.subprocess.PIPE
    )


async def run_for(
    n: int,
    loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
) -> None:
    """
    Return after a set amount of time,
    cancelling all other tasks before doing so.
    """
    start = loop.time()

    while True:

        await asyncio.sleep(0)

        if abs(loop.time() - start) > n:
            # cancel all other tasks
            for task in asyncio.Task.all_tasks(loop):
                if task is not asyncio.Task.current_task():
                    task.cancel()
            return


with event_loop() as loop:
    coroutines = (read_json_from_subprocess() for _ in range(5))
    # create Task from coroutines and schedule
    # it for execution on the event loop
    asyncio.gather(*coroutines)  # this returns a Task and schedules it implicitly

    loop.run_until_complete(run_for(5))
```

    <_GatheringFuture pending>



    ERROR:root:JSONDecodeError for input: printer.py in process 92541 waiting 4 seconds to print json string
    ERROR:root:JSONDecodeError for input: printer.py in process 92540 waiting 4 seconds to print json string
    ERROR:root:JSONDecodeError for input: printer.py in process 92542 waiting 4 seconds to print json string
    ERROR:root:JSONDecodeError for input: printer.py in process 92543 waiting 2 seconds to print json string
    ERROR:root:JSONDecodeError for input: printer.py in process 92544 waiting 2 seconds to print json string
    ERROR:root:JSONDecodeError for input: printer.py in process 92544 waiting 3 seconds to print json string
    ERROR:root:JSONDecodeError for input: printer.py in process 92543 waiting 1 seconds to print json string


    <Process 92544> -> {'current_time': 'Mon Sep 25 16:25:21 2017', 'words': 'threadway:redroot:perfidious'}
    <Process 92543> -> {'current_time': 'Mon Sep 25 16:25:21 2017', 'words': 'Ebionitism:procidence:Olpidium'}


    ERROR:root:JSONDecodeError for input: printer.py in process 92543 waiting 1 seconds to print json string


    <Process 92543> -> {'current_time': 'Mon Sep 25 16:25:22 2017', 'words': 'octantal:joculator'}


    ERROR:root:JSONDecodeError for input: printer.py in process 92540 waiting 0 seconds to print json string
    ERROR:root:JSONDecodeError for input: printer.py in process 92540 waiting 4 seconds to print json string
    ERROR:root:JSONDecodeError for input: printer.py in process 92541 waiting 2 seconds to print json string
    ERROR:root:JSONDecodeError for input: printer.py in process 92542 waiting 3 seconds to print json string
    ERROR:root:JSONDecodeError for input: printer.py in process 92543 waiting 3 seconds to print json string


    <Process 92540> -> {'current_time': 'Mon Sep 25 16:25:23 2017', 'words': 'postclival:milammeter:gnathobase'}
    <Process 92540> -> {'current_time': 'Mon Sep 25 16:25:23 2017', 'words': 'Deuteronomic:photovoltaic'}
    <Process 92541> -> {'current_time': 'Mon Sep 25 16:25:23 2017', 'words': 'starwort:combure'}
    <Process 92542> -> {'current_time': 'Mon Sep 25 16:25:23 2017', 'words': 'infixion:Ailurus:effectualness'}
    <Process 92543> -> {'current_time': 'Mon Sep 25 16:25:23 2017', 'words': 'Phoenicopteridae:Platyctenea:palpitatingly'}
    
    
    ---loop closed---
    
    


## Conclusion

In our example, we spawn multiple instances of `printer.py` as subprocesses to get an idea of how the event loop intelligently delegates control to between multiple Tasks when it encounters an `await`.

Although asyncio as a framework has a bit of a learning curve, in no small part due to its wonky api, (a **Task** is a **Future** that can be instantiated and scheduled with `ensure_future` or `loop.create_task` anyone?), it has many benefits in that it already has well-defined abstractions on top of common interfaces like subprocesses, file-descriptors, and sockets. That alone -- not having to write non-blocking code that knows how and when to poll those [different interfaces](https://docs.python.org/3/library/asyncio-stream.html) -- is enough to be excited about asyncio, in my opinion.


