from box import Box

from litman.db_connector import DB

STATE = {}


def get_globals() -> tuple[Box, DB]:
    return STATE["config"], STATE["db"]
