from enum import Enum
from typing import NamedTuple


class CollectMode(Enum):
    CANDY = "candy"
    CARD = "card"

class BatchResult(NamedTuple):
    candies: int
    cards_found: int
