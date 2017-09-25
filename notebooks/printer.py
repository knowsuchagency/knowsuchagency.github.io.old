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