from typing import Protocol


class IRobotLogger(Protocol):
    def success(self, message: str):
        """Логирование уровня SUCCESS."""
        ...

    def debug(self, message: str) -> None:
        """Логирование уровня DEBUG."""
        ...

    def info(self, message: str) -> None:
        """Логирование уровня INFO."""
        ...

    def error(self, message: str) -> None:
        """Логирование уровня ERROR."""
        ...

    def critical(self, message: str) -> None:
        """Логирование уровня CRITICAL."""
        ...
