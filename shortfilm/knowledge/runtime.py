"""Small runtime loader for production knowledge cards."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def get_card(card_id: str = "coffee_modern_realism_v1") -> dict:
    cards = json.loads((ROOT / "coffee_ads.json").read_text(encoding="utf-8"))
    for card in cards:
        if card.get("id") == card_id:
            return card
    raise KeyError(card_id)

