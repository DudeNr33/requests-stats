from typing import NamedTuple


class Recording(NamedTuple):
    method: str
    scheme: str
    netloc: str
    path: str
    params: str
    query: str
    response_code: int
    duration: float
