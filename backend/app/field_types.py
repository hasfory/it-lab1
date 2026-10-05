from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Dict

from .errors import ValidationError


# ---------------------------------------------------------------- комплексні --
@dataclass(frozen=True)
class Complex:
    """Комплексне число re + im*i (частини можуть бути int або float)."""
    re: float
    im: float

    def modulus_sq(self) -> float:
        return self.re * self.re + self.im * self.im

    def __str__(self) -> str:
        return _format_complex(self.re, self.im)


def _fmt(x) -> str:
    if isinstance(x, float) and x.is_integer() and abs(x) < 1e15:
        return str(int(x))
    return repr(x) if isinstance(x, float) else str(x)


def _format_complex(re_: float, im: float) -> str:
    sign = "-" if (im < 0 or (isinstance(im, float) and math.copysign(1, im) < 0 and im == 0)) else "+"
    return f"{_fmt(re_)}{sign}{_fmt(abs(im))}i"


_INT = r"[+-]?\d+"
_UINT = r"\d+"
_REAL = r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?"
_UREAL = r"(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?"


def _build_patterns(num: str, unum: str):
    full = re.compile(rf"^(?P<re>{num})(?P<sign>[+-])(?P<im>{unum})?i$")
    imag = re.compile(rf"^(?P<sign>[+-])?(?P<im>{unum})?i$")
    real = re.compile(rf"^(?P<re>{num})$")
    return full, imag, real


_INT_PATTERNS = _build_patterns(_INT, _UINT)
_REAL_PATTERNS = _build_patterns(_REAL, _UREAL)


def _parse_complex(text: str, patterns, conv, type_name: str) -> Complex:
    s = text.replace(" ", "")
    if not s:
        raise ValidationError(f"Порожнє значення для типу {type_name}")
    full, imag, real = patterns
    try:
        m = full.match(s)
        if m:
            im = conv(m.group("im") or "1")
            if m.group("sign") == "-":
                im = -im
            return Complex(conv(m.group("re")), im)
        m = imag.match(s)
        if m:
            im = conv(m.group("im") or "1")
            if m.group("sign") == "-":
                im = -im
            return Complex(conv("0"), im)
        m = real.match(s)
        if m:
            return Complex(conv(m.group("re")), conv("0"))
    except (ValueError, OverflowError):
        pass
    example = "3+4i" if type_name == "complexInteger" else "2.5-1.3i"
    raise ValidationError(
        f"'{text}' не є коректним значенням типу {type_name} (приклад: {example})"
    )


# ---------------------------------------------------------------- базовий тип --
class FieldType:
    name: str = ""

    def parse(self, raw: Any):
        raise NotImplementedError

    def to_str(self, value) -> str:
        return str(value)

    def to_json(self, value):
        return value

    def from_json(self, data):
        return self.parse(data)

    def sort_key(self, value):
        return value


class IntegerType(FieldType):
    name = "integer"

    def parse(self, raw):
        if isinstance(raw, bool):
            raise ValidationError("Булеве значення не є integer")
        if isinstance(raw, int):
            return raw
        if isinstance(raw, str) and re.fullmatch(r"\s*[+-]?\d+\s*", raw):
            return int(raw)
        raise ValidationError(f"'{raw}' не є цілим числом (integer)")


class RealType(FieldType):
    name = "real"

    def parse(self, raw):
        if isinstance(raw, bool):
            raise ValidationError("Булеве значення не є real")
        try:
            val = float(raw) if not isinstance(raw, str) else float(raw.strip().replace(",", "."))
        except (TypeError, ValueError):
            raise ValidationError(f"'{raw}' не є дійсним числом (real)")
        if math.isnan(val) or math.isinf(val):
            raise ValidationError("NaN та нескінченність недопустимі для real")
        return val


class CharType(FieldType):
    name = "char"

    def parse(self, raw):
        if not isinstance(raw, str) or len(raw) != 1:
            raise ValidationError(f"'{raw}' не є одним символом (char)")
        return raw

    def sort_key(self, value):
        return (_text_key(value), value)


_UK_ALPHABET = "абвгґдеєжзиіїйклмнопрстуфхцчшщьюя"
_UK_ORDER = {ch: i for i, ch in enumerate(_UK_ALPHABET)}


def _text_key(text: str):
    key = []
    for ch in text.casefold():
        if ch in _UK_ORDER:
            key.append((1, _UK_ORDER[ch]))
        else:
            key.append((0, ord(ch)))
    return key


class StringType(FieldType):
    name = "string"

    def parse(self, raw):
        if not isinstance(raw, str):
            raise ValidationError(f"'{raw}' не є рядком (string)")
        return raw

    def sort_key(self, value):
        return (_text_key(value), value)


class _ComplexBase(FieldType):
    """Спільна логіка: порівняння за модулем, при рівності - за re, потім im."""

    def to_str(self, value) -> str:
        return str(value)

    def to_json(self, value):
        return {"re": value.re, "im": value.im}

    def from_json(self, data):
        if isinstance(data, dict) and "re" in data and "im" in data:
            return self._make(data["re"], data["im"])
        return self.parse(data)

    def sort_key(self, value: Complex):
        return (value.modulus_sq(), value.re, value.im)

    def _make(self, re_, im):
        raise NotImplementedError


class ComplexIntegerType(_ComplexBase):
    name = "complexInteger"

    def parse(self, raw):
        if isinstance(raw, Complex):
            return self._make(raw.re, raw.im)
        if not isinstance(raw, str):
            raise ValidationError(f"'{raw}' не є значенням типу complexInteger")
        return _parse_complex(raw, _INT_PATTERNS, int, self.name)

    def _make(self, re_, im):
        for part in (re_, im):
            if isinstance(part, bool) or (isinstance(part, float) and not part.is_integer()) \
                    or not isinstance(part, (int, float)):
                raise ValidationError("Частини complexInteger мають бути цілими")
        return Complex(int(re_), int(im))


class ComplexRealType(_ComplexBase):
    name = "complexReal"

    def parse(self, raw):
        if isinstance(raw, Complex):
            return self._make(raw.re, raw.im)
        if not isinstance(raw, str):
            raise ValidationError(f"'{raw}' не є значенням типу complexReal")
        z = _parse_complex(raw, _REAL_PATTERNS, float, self.name)
        return self._make(z.re, z.im)

    def _make(self, re_, im):
        for part in (re_, im):
            if isinstance(part, bool) or not isinstance(part, (int, float)) \
                    or math.isnan(part) or math.isinf(part):
                raise ValidationError("Частини complexReal мають бути скінченними числами")
        return Complex(float(re_), float(im))


# ------------------------------------------------------------------- реєстр --
TYPES: Dict[str, FieldType] = {
    t.name: t
    for t in (
        IntegerType(), RealType(), CharType(), StringType(),
        ComplexIntegerType(), ComplexRealType(),
    )
}


def get_type(name: str) -> FieldType:
    try:
        return TYPES[name]
    except KeyError:
        raise ValidationError(
            f"Невідомий тип '{name}'. Допустимі: {', '.join(TYPES)}"
        )