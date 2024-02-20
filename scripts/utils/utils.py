################## makedirs ##################
import datetime, random, string, os
from pathlib import Path
from functools import wraps


def generate_random_string(length:int=4) -> str:
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))

def makedirs(
    prefix: str = "results",
    date: bool = True,
    randomID: bool = True
) -> Path:
    name = str(prefix)
    if date:
        now = datetime.datetime.now()
        date = now.strftime('%Y%m%d%H%M%S')
        name += f"_{date}"
    if randomID:
        name += f"_{generate_random_string(8)}"
    os.makedirs(name, exist_ok=True)
    return Path(name)
################## makedirs ##################