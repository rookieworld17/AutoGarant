"""User-facing text templates (the "View" layer).

Keeping copy here makes it trivial to edit wording or add localization later.
"""
from __future__ import annotations


def welcome(full_name: str | None) -> str:
    name = full_name or "there"
    return (
        f"👋 Welcome to <b>AutoGarant</b>, {name}!\n\n"
        "I'm your assistant bot. Use the menu below to get started."
    )


def welcome_back(full_name: str | None) -> str:
    name = full_name or "there"
    return f"👋 Welcome back, {name}!"


HELP = (
    "<b>AutoGarant — help</b>\n\n"
    "/start — start / restart the bot\n"
    "/help — show this message"
)

UNKNOWN = "🤔 I didn't understand that. Try /help to see what I can do."
