from __future__ import annotations


def split_index_msg(entry_type: str, value: str) -> list[str]:
    # new entry types must be listed in util/nodes.py!
    if entry_type == 'single':
        try:
            return split_into(2, 'single', value)
        except ValueError:
            return split_into(1, 'single', value)
    if entry_type == 'pair':
        return split_into(2, 'pair', value)
    if entry_type == 'triple':
        return split_into(3, 'triple', value)
    if entry_type in {'see', 'seealso'}:
        return split_into(2, 'see', value)
    raise ValueError(f'invalid {entry_type} index entry {value!r}')


def split_into(n: int, type: str, value: str) -> list[str]:
    """Split an index entry into a given number of parts at semicolons."""
    parts = [x.strip() for x in value.split(';', n - 1)]
    if len(list(filter(None, parts))) < n:
        raise ValueError(f'invalid {type} index entry {value!r}')
    return parts
