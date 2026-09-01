"""Backward-compatible imports for the structured logging module."""

from app.core.logging import configure_logging, get_logger

__all__ = ["configure_logging", "get_logger"]
