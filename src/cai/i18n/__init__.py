"""
CAI Internationalization (i18n) Module

Provides multi-language support for CAI CLI/TUI messages.
Set CAI_LANGUAGE environment variable to change language (default: "en").
Supported: "en", "ko"
"""

import os
from cai.i18n.messages import MESSAGES

_current_language = os.getenv("CAI_LANGUAGE", "en")


def set_language(lang: str):
    global _current_language
    if lang in MESSAGES:
        _current_language = lang
        os.environ["CAI_LANGUAGE"] = lang


def get_language() -> str:
    return _current_language


def t(key: str, **kwargs) -> str:
    lang = os.getenv("CAI_LANGUAGE", _current_language)
    msg = MESSAGES.get(lang, MESSAGES["en"]).get(key)
    if msg is None:
        msg = MESSAGES["en"].get(key, key)
    if kwargs:
        try:
            return msg.format(**kwargs)
        except (KeyError, IndexError):
            return msg
    return msg
