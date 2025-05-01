from loguru import logger
import sys
import os
from pathlib import Path

def setup_logging():
    """
    Configure loguru logger with proper formatting and log file setup.
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Remove default handler
    logger.remove()

    # # Add console handler with custom format
    # logger.add(
    #     sys.stderr,
    #     format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    #     level="INFO",
    #     colorize=True,
    # )

    # Add file handler for all logs
    logger.add(
        log_dir / "app.log",
        rotation="10 MB",  # Rotate when file reaches 10MB
        retention="1 month",  # Keep logs for 1 month
        compression="zip",  # Compress rotated logs
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        backtrace=True,
        diagnose=True,
    )

    # Add file handler for errors only
    logger.add(
        log_dir / "error.log",
        rotation="10 MB",
        retention="1 month",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        backtrace=True,
        diagnose=True,
    )

    return logger

# Initialize logger
logger = setup_logging()