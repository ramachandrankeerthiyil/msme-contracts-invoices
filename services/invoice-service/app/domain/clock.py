"""Business "today" (architecture.md: evaluated in APP_TIMEZONE, Asia/Kolkata)."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import Request


def today_in(time_zone: str) -> date:
    return datetime.now(ZoneInfo(time_zone)).date()


def local_date(moment: datetime, time_zone: str) -> date:
    return moment.astimezone(ZoneInfo(time_zone)).date()


def get_today(request: Request) -> date:
    """FastAPI dependency. Tests pin the date via `app.dependency_overrides[get_today]`."""
    return today_in(request.app.state.settings.app_timezone)
