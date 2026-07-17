import re
from dataclasses import dataclass, field


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
    # v0.7.3 role-aware extraction
    role: str = "rent"                      # rent | ipl | deposit | service | area | unrelated | unknown
    rent_figure: int | None = None          # primary rent amount in its native period
    area_text: str | None = None            # captured dimension/area text
    candidates: list = field(default_factory=list)   # all tagged money/area candidates
    normalized_note: str = ""


_MAGNITUDES = {"rb": 1_000, "ribu": 1_000, "k": 1_000,
               "jt": 1_000_000, "juta": 1_000_000, "m": 1_000_000,
               "million": 1_000_000}
_NUMBER = r"(?:\d+(?:[.,]\d{3})+|\d+(?:[.,]\d+)?)"
# group1=rp prefix, group2=number, group3=magnitude suffix
_TOKEN = re.compile(rf"(?:(rp\.?|Rp\.?)\s*)?({_NUMBER})\s*(rb|ribu|k|jt|juta|m|million)?\b", re.I)
_AREA_TOKEN = re.compile(rf"(\d+(?:[.,]\d+)?)\s*(m2|mtr|meter|m)\b", re.I)
_AREA_KW = re.compile(r"\b(luas|ukuran|uk\.|lt\.|lb\.|kamar|dimensi|lebar|panjang)\b")
_PERIOD_RE = {
    "month": re.compile(r"(?:/\s*bln|/\s*bulan|per\s+bln|per\s+bulan|sebulan|bulanan|/\s*mo|per\s+month|monthly)", re.I),
    "year": re.compile(r"(?:/\s*thn|/\s*tahun|per\s+thn|per\s+tahun|setahun|tahunan|/\s*yr|per\s+year|\byear\b|annual)", re.I),
}
# Order matters: charge roles win over generic rent so IPL/deposit are not swallowed.
_RENT_KW = re.compile(r"(harga sewa|harga|sewa|rent|price|rate|per\s+tahun|per\s+bulan|/\s*bln|/\s*thn)", re.I)
_IPL_KW = re.compile(r"\b(ipl|service charge|service|maintenance|perawatan)\b")
_DEPOSIT_KW = re.compile(r"\b(deposit|dp|uang muka|booking fee|booking)\b")


def _number(value: str, multiplier: int = 1) -> int:
    if "," in value and "." in value:
        value = value.replace(".", "").replace(",", ".")
    elif "," in value:
        value = value.replace(",", ".")
    elif value.count(".") > 1 or ("." in value and len(value.rsplit(".", 1)[1]) == 3):
        value = value.replace(".", "")
    return int(round(float(value) * multiplier))


def _detect_period(text: str) -> str | None:
    if _PERIOD_RE["month"].search(text):
        return "month"
    if _PERIOD_RE["year"].search(text):
        return "year"
    return None


def _token_role(before: str, has_rp_prefix: bool, has_mag: bool) -> str:
    if _IPL_KW.search(before):
        return "ipl"
    if _DEPOSIT_KW.search(before):
        return "deposit"
    if _RENT_KW.search(before) or has_rp_prefix:
        return "rent"
    if has_mag:
        return "rent"
    return "unrelated"


def parse_budget(text: str) -> BudgetResult:
    raw = text or ""
    low = raw.lower()
    period_global = _detect_period(low)
    candidates: list[dict] = []
    area_texts: list[str] = []

    for line in raw.splitlines():
        llow = line.lower()
        line_period = _detect_period(llow) or period_global

        # Explicit "a-b <unit>" range (e.g. "3-4 juta", "1jt - 2jt/bulan"). The numbers
        # may lack a magnitude suffix when the unit trails only the second token; bind the
        # range's suffix to BOTH endpoints so the first value is not dropped as "bare".
        range_match = re.search(
            rf"({_NUMBER})\s*[-–]\s*({_NUMBER})\s*(rb|ribu|k|jt|juta|m|million)\b", llow, re.I)
        range_lo = range_hi = range_suffix = None
        if range_match:
            range_lo = _number(range_match.group(1), 1)
            range_hi = _number(range_match.group(2), 1)
            range_suffix = range_match.group(3).lower()
            range_amount = _MAGNITUDES[range_suffix]
            # Seed two rent candidates for the range so it is handled uniformly below.
            before = llow[max(0, range_match.start() - 24):range_match.start()]
            role = "rent" if (_RENT_KW.search(before) or not (_IPL_KW.search(before)
                   or _DEPOSIT_KW.search(before))) else (
                   "ipl" if _IPL_KW.search(before) else "deposit")
            line_items_range = [
                {"role": role, "amount": range_lo * range_amount, "period": line_period,
                 "raw": range_match.group(0).strip(), "has_mag": True, "idx": range_match.start()},
                {"role": role, "amount": range_hi * range_amount, "period": line_period,
                 "raw": range_match.group(0).strip(), "has_mag": True,
                 "idx": range_match.end() - 1},
            ]
            candidates.extend(line_items_range)
            # Skip the individual _TOKEN hits that fall inside the range span.
            range_span = range_match.span()

        # Capture dimension/area tokens (never money).
        for am in _AREA_TOKEN.finditer(llow):
            unit = am.group(2).lower()
            aw = llow[max(0, am.start() - 22):am.start()]
            if _AREA_KW.search(aw) or unit in ("m2", "mtr", "meter"):
                area_texts.append(am.group(0).strip())

        toks = list(_TOKEN.finditer(llow))
        line_items: list[dict] = []
        for m in toks:
            if range_match and range_match.start() <= m.start() < range_match.end():
                continue  # already represented by the range candidates
            rp_prefix = bool(m.group(1))
            number = m.group(2)
            suffix = (m.group(3) or "").lower()
            before = llow[max(0, m.start() - 24):m.start()]
            # Dimension (area) exclusion: "23m", "12mtr", "3m2" near an area keyword.
            if suffix in ("m", "m2", "mtr", "meter"):
                aw = llow[max(0, m.start() - 22):m.start()]
                if _AREA_KW.search(aw) or suffix in ("m2", "mtr", "meter"):
                    continue  # area, not money
            has_mag = bool(suffix) or rp_prefix
            if not (rp_prefix or has_mag or _IPL_KW.search(before)
                    or _DEPOSIT_KW.search(before) or _RENT_KW.search(before)):
                continue  # bare number with no monetary context -> ignore
            role = _token_role(before, rp_prefix, has_mag)
            if role == "unrelated":
                continue
            amount = _number(number, _MAGNITUDES.get(suffix, 1))
            line_items.append({
                "role": role, "amount": amount, "period": line_period,
                "raw": m.group(0).strip(), "has_mag": has_mag, "idx": m.start(),
            })
        candidates.extend(line_items)

    rent = [c for c in candidates if c["role"] == "rent"]
    ipl = [c for c in candidates if c["role"] == "ipl"]
    deposit = [c for c in candidates if c["role"] == "deposit"]
    area = " ".join(area_texts) or None

    if rent:
        # Range detection: two rent tokens on the same line joined by a dash.
        rent_range = None
        if len(rent) >= 2 and re.search(r"\s*[-–]\s*", llow[rent[0]["idx"]:rent[1]["idx"] + 1]):
            lo, hi = sorted((rent[0]["amount"], rent[1]["amount"]))
            rent_range = (lo, hi)
        if rent_range:
            lo, hi = rent_range
        else:
            vals = [c["amount"] for c in rent]
            lo, hi = min(vals), max(vals)
        periods = [c["period"] for c in rent if c["period"]]
        period = periods[0] if periods else "unknown"

        if period == "year":
            return BudgetResult(
                raw_text=raw, min_amount=lo, max_amount=hi, period="year",
                confidence="high", role="rent", rent_figure=lo, area_text=area,
                original_yearly=lo if lo == hi else (lo, hi),
                monthly_min=lo // 12, monthly_max=hi // 12,
                candidates=candidates,
                note="rent" + (" range" if rent_range else "") + " extracted yearly; IPL/deposit/area excluded",
                normalized_note="normalized yearly -> monthly",
            )
        if period == "month":
            return BudgetResult(
                raw_text=raw, min_amount=lo, max_amount=hi, period="month",
                confidence="high", role="rent", rent_figure=lo, area_text=area,
                monthly_min=lo, monthly_max=hi,
                candidates=candidates,
                note="rent" + (" range" if rent_range else "") + " extracted monthly; IPL/deposit/area excluded",
                normalized_note="monthly rent preserved",
            )
        return BudgetResult(
            raw_text=raw, min_amount=lo, max_amount=hi, period="unknown",
            confidence="medium", role="rent", rent_figure=lo, area_text=area,
            monthly_min=lo, monthly_max=hi,
            candidates=candidates,
            note="rent amount without explicit period; IPL/deposit/area excluded",
            normalized_note="period unknown",
        )

    if ipl or deposit or area:
        which = []
        if ipl:
            which.append("ipl/service")
        if deposit:
            which.append("deposit")
        if area:
            which.append("area")
        return BudgetResult(
            raw_text=raw,
            period=(ipl[0]["period"] if ipl else "unknown"),
            confidence="low", role="ipl" if ipl else ("deposit" if deposit else "area"),
            area_text=area, candidates=candidates,
            note="no rent figure; found " + ", ".join(which),
        )

    return BudgetResult(
        raw_text=raw, period=period_global or "unknown", confidence="low",
        note="ambiguous number without magnitude", candidates=candidates,
    )
