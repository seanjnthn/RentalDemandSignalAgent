import re
from dataclasses import dataclass


@dataclass
class BudgetResult:
    raw_text: str
    min_amount: int | None = None
    max_amount: int | None = None
    currency: str = "IDR"
    period: str = "unknown"
    confidence: str = "low"
    note: str = ""
    monthly_min: int | None = None
    monthly_max: int | None = None
    original_yearly: int | tuple[int, int] | None = None


_MAGNITUDES = {"rb": 1_000, "ribu": 1_000, "k": 1_000,
               "jt": 1_000_000, "juta": 1_000_000, "m": 1_000_000,
               "million": 1_000_000}
_NUMBER = r"(?:\d+(?:[.,]\d{3})+|\d+(?:[.,]\d+)?)"
_TOKEN = re.compile(rf"(?:rp\s*)?({_NUMBER})\s*(rb|ribu|k|jt|juta|m|million)?\b", re.I)


def _number(value: str, multiplier: int = 1) -> int:
    if "," in value and "." in value:
        value = value.replace(".", "").replace(",", ".")
    elif "," in value:
        value = value.replace(",", ".")
    elif value.count(".") > 1 or ("." in value and len(value.rsplit(".", 1)[1]) == 3):
        value = value.replace(".", "")
    return int(round(float(value) * multiplier))


def parse_budget(text: str) -> BudgetResult:
    raw = text or ""
    low = raw.lower()
    if re.search(r"(?:/\s*bln|/\s*bulan|per\s+bln|per\s+bulan|sebulan|bulanan|/\s*mo|per\s+month|monthly)", low): period = "month"
    elif re.search(r"(?:/\s*thn|/\s*tahun|per\s+thn|per\s+tahun|setahun|tahunan|/\s*yr|per\s+year|\byear\b|annual)", low): period = "year"
    else: period = "unknown"
    range_match = re.search(rf"({_NUMBER})\s*[-–]\s*({_NUMBER})\s*(rb|ribu|k|jt|juta|m|million)\b", low, re.I)
    if range_match:
        suffix = range_match.group(3).lower()
        amounts = (_number(range_match.group(1), _MAGNITUDES[suffix]), _number(range_match.group(2), _MAGNITUDES[suffix]))
        result = BudgetResult(raw_text=raw, min_amount=amounts[0], max_amount=amounts[1], period=period,
                              confidence="high" if period in ("month", "year") else "medium", note="normalized budget")
        if period == "year":
            result.original_yearly = amounts[0] if amounts[0] == amounts[1] else amounts
            result.monthly_min, result.monthly_max = amounts[0] // 12, amounts[1] // 12
        elif period == "month": result.monthly_min, result.monthly_max = amounts
        return result
    candidates = []
    for m in _TOKEN.finditer(low):
        number, suffix = m.group(1), (m.group(2) or "").lower()
        before = low[max(0, m.start() - 18):m.start()]
        explicit = bool(suffix or m.group(0).startswith("rp") or re.search(r"rp\s*$", before) or re.search(r"(?:budget|anggaran|harga)\s*$", before))
        if explicit and not (not suffix and re.search(r"(?:br|bedroom|kamar)\s*$", before)):
            candidates.append((m, _number(number, _MAGNITUDES.get(suffix, 1)), bool(suffix)))
    if not candidates:
        return BudgetResult(raw_text=raw, period=period, confidence="low", note="ambiguous number without magnitude")
    values = [item[1] for item in candidates]
    if len(candidates) >= 2 and re.search(r"\s*[-–]\s*", low[candidates[0][0].end():candidates[1][0].start()]):
        amounts = (values[0], values[1])
    else:
        amounts = (min(values), max(values)) if len(values) > 1 else (values[0], values[0])
    has_magnitude = any(item[2] for item in candidates)
    if not has_magnitude and any(value < 100_000 for value in amounts):
        return BudgetResult(raw_text=raw, period=period, confidence="low", note="ambiguous number without magnitude")
    result = BudgetResult(raw_text=raw, min_amount=amounts[0], max_amount=amounts[1], period=period,
                          confidence="high" if has_magnitude and period in ("month", "year") else "medium",
                          note="normalized budget")
    if period == "year":
        result.original_yearly = amounts[0] if amounts[0] == amounts[1] else amounts
        result.monthly_min, result.monthly_max = amounts[0] // 12, amounts[1] // 12
    elif period == "month": result.monthly_min, result.monthly_max = amounts
    return result
