"""Status simples do serviço, exposto em GET /api/status."""
import time

from .. import repository
from ..markets import MARKETS

_started_at = time.time()


def get_status() -> dict:
    return {
        "started_at": _started_at,
        "uptime_seconds": time.time() - _started_at,
        "markets": {
            key: {"last_updated_at": repository.get_last_updated(key)}
            for key in MARKETS
        },
    }
