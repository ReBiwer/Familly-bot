"""Middleware для бота."""

from src.presentation.bot.middlewares.auth import AuthMiddleware

__all__ = ["AuthMiddleware"]
