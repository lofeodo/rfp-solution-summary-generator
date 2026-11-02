"""Quote matching lives in the package since S5 (``rfp_agent.textmatch``); this module
re-exports it so the gold scripts and tests keep their imports."""

from rfp_agent.textmatch import find_quote, normalise

__all__ = ["find_quote", "normalise"]
