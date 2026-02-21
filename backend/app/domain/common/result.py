"""Result<T> pattern — domain functions return this instead of raising exceptions for normal flow."""
from __future__ import annotations
from typing import TypeVar, Generic, Optional

T = TypeVar("T")


class Result(Generic[T]):
    def __init__(self, is_success: bool, value: Optional[T] = None, error: Optional[str] = None):
        self.is_success = is_success
        self.value = value
        self.error = error

    @classmethod
    def ok(cls, value: T) -> "Result[T]":
        return cls(is_success=True, value=value)

    @classmethod
    def fail(cls, error: str) -> "Result[T]":
        return cls(is_success=False, error=error)

    def __repr__(self) -> str:
        if self.is_success:
            return f"Result.ok({self.value!r})"
        return f"Result.fail({self.error!r})"
