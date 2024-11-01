"""Helper functions.

These can be used in entity definitions
"""

from functools import reduce
import logging

_LOGGER = logging.getLogger(__name__)


def get_key(
    dot_notation_path: str, data: dict, value_if_none: str | float | None = None
) -> dict[str, dict | str | int] | str | int:
    """Try to get a deep value from a dict based on a dot-notation."""
    if dot_notation_path == "":
        return data

    if dot_notation_path is None:
        return None

    dn_list = dot_notation_path.split(".")

    try:
        return reduce(get_data, dn_list, data)
    except (TypeError, KeyError) as ex:
        _LOGGER.error("TYPE ERROR: %s - %s", dn_list, ex)
        return None


def get_data(data: dict | list, key: str) -> dict | list | None:
    """Get data from key.

    If key is in format 1|id then get data from that key with value specified.
    """
    if data is None:
        return None

    if "|" in key:
        # get data from field with value
        info = key.split("|")
        value = info[0]
        field = info[1]
        for entry in data:
            if entry.get(field) == value:
                return entry
        return None

    return data.get(str(key))


def slugify(value: str) -> str | None:
    """Slugify value."""
    if value:
        return value.replace(" ", "_").replace(".", "_").lower()
    return None
