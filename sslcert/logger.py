import logging
from pathlib import Path

logger = logging.getLogger("ssl-cert")
_formatter = logging.Formatter(
    fmt="{asctime} [{filename}:{lineno:>3d}] {levelname:<5s}: {message}",
    datefmt="%Y-%m-%d %H:%M:%S",
    style="{",
)

logger.handlers.clear()
console_handler = logging.StreamHandler()
console_handler.setFormatter(_formatter)
console_handler.setLevel(logging.DEBUG)

log_folder = Path(__file__).parent.parent / "logs"
log_folder.mkdir(exist_ok=True)

file_handler = logging.FileHandler(filename=log_folder / "sslcert.log")
file_handler.setFormatter(_formatter)
file_handler.setLevel(logging.DEBUG)

logger.addHandler(console_handler)
logger.addHandler(file_handler)
logger.setLevel(logging.DEBUG)
