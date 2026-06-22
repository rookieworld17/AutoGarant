"""Controllers package — aggregates all routers.

Import ``routers`` and include them into the dispatcher in order.
"""
from app.controllers import common, start

# Order matters: specific routers first, the catch-all (common) last.
routers = (
    start.router,
    common.router,
)

__all__ = ["routers"]
