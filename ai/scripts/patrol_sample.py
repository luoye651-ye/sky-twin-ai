"""Repeatable sampling from the fixed image pool, never from prediction scores."""
import random


def select_records(records, count, seed):
    if not isinstance(count, int) or not 1 <= count <= len(records) <= 132:
        raise ValueError("Patrol count must be within 1..132 and available pool")
    pool = sorted(records, key=lambda item: item['id'])
    if len({item['id'] for item in pool}) != len(pool):
        raise ValueError("Duplicate pool image IDs")
    return sorted(random.Random(seed).sample(pool, count), key=lambda item: item['id'])
