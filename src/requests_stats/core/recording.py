from typing import NamedTuple


class Recording(NamedTuple):
    method: str
    url: str
    params: str
    response_code: int
    duration: float
