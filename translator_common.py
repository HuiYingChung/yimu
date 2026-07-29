"""Shared primitives for Yimu's live translation providers.

Keep provider-neutral errors and text helpers here so the Gemini and OpenAI
implementations do not depend on each other.
"""

import re


class FatalTranslatorError(RuntimeError):
    """Unrecoverable provider error, such as an invalid API key."""


# Keep only letters, digits and CJK so half/full-width punctuation and
# spacing differences do not break echo comparison.
_NORM_RE = re.compile(r"[^0-9a-z一-鿿]+")
_CJK_RE = re.compile(r"[一-鿿]")


def _normalize(text: str) -> str:
    return _NORM_RE.sub("", text.lower())


def _leaf_errors(exc: BaseException) -> list[BaseException]:
    """Flatten nested ExceptionGroups into their leaf exceptions.

    TaskGroup wraps child failures in an ExceptionGroup, so neither
    ``except FatalTranslatorError`` nor substring checks on ``str(exc)`` see
    the real error without unwrapping first.
    """
    if isinstance(exc, BaseExceptionGroup):
        leaves: list[BaseException] = []
        for sub in exc.exceptions:
            leaves.extend(_leaf_errors(sub))
        return leaves
    return [exc]
