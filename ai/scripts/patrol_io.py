"""Windows readers briefly deny replacement of an otherwise atomic JSON file."""
import time


def replace_with_retry(source, target):
    for attempt in range(40):
        try:
            source.replace(target)
            return
        except PermissionError:
            if attempt == 39:
                raise
            time.sleep(.025)
