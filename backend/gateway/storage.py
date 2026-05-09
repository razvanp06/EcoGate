from __future__ import annotations
import json
import logging
import os
from collections import deque
from typing import Optional

from shared.models import GreenReceipt

_RECEIPTS: deque[dict] = deque(maxlen=500)
_FILE_PATH = "/tmp/ecogate_receipts.json"

logger = logging.getLogger(__name__)


def _load_from_disk() -> None:
    """Populate the in-memory deque from the persistence file on cold start."""
    if not os.path.exists(_FILE_PATH):
        return
    try:
        with open(_FILE_PATH, "r") as f:
            saved = json.load(f)
        for item in saved[-500:]:
            _RECEIPTS.append(item)
        logger.info("Loaded %d receipts from disk.", len(_RECEIPTS))
    except Exception as exc:
        logger.warning("Could not load receipts from disk: %s", exc)


def _save_to_disk() -> None:
    try:
        with open(_FILE_PATH, "w") as f:
            json.dump(list(_RECEIPTS), f)
    except Exception as exc:
        logger.warning("Could not persist receipts to disk: %s", exc)


# Load on module import (runs once per warm instance)
_load_from_disk()


def append_receipt(receipt: GreenReceipt) -> None:
    _RECEIPTS.append(receipt.to_dict())
    _save_to_disk()


def get_recent_receipts(n: int = 100) -> list[dict]:
    all_receipts = list(_RECEIPTS)
    return all_receipts[-n:]
