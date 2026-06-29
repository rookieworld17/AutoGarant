"""Controllers package — aggregates all routers.

Import ``routers`` and include them into the dispatcher in order.
"""
from app.controllers import admin, common, start

routers = (
    admin.router,
    start.router,
    common.router,
)

__all__ = ["routers"]
