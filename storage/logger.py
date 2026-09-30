from __future__ import annotations

import logging
from pathlib import Path


class ProjectLogger:
    def __init__(
        self,
        log_dir="logs",
        name="wn-translator",
    ):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        if not self.logger.handlers:
            log_path = self.log_dir / "translator.log"

            handler = logging.FileHandler(
                log_path,
                encoding="utf-8",
            )

            formatter = logging.Formatter(
                "%(asctime)s | %(levelname)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    @property
    def path(self) -> Path:
        return self.log_dir / "translator.log"

    def info(self, message: str):
        self.logger.info(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def error(self, message: str):
        self.logger.error(message)

    def exception(self, message: str):
        self.logger.exception(message)
