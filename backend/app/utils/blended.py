"""The blended discount risk engine.

Two independent paths, and the higher level wins. A single aggregate cannot
satisfy the brief, because PS section 10 asks for two things that pull apart:

  - one $450 service line 8pt over must flag a $3,030 quotation, however small
    its share of the order
  - many lines each slightly over must not slip through

A value-weighted average alone fails the first: it dilutes the offending line to
about 1.2pt and routes it LOW, the opposite of the wireframe. So the worst line
is scored separately and max() decides.
"""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from app.models.enums import DecidedBy, RiskLevel

_ORDER = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2}
_ZERO = Decimal("0")


@dataclass(frozen=True)
class ScoredLine:
    product: str
    list_value: Decimal
    excess_pt: Decimal
    excess_value: Decimal


@dataclass(frozen=True)
class RiskThresholds:
    """Cut-points, read from the risk_thresholds table."""

    worst_medium_pt: Decimal = Decimal("0.01")
    worst_high_pt: Decimal = Decimal("5")
    blended_medium_pt: Decimal = Decimal("1")
    blended_high_pt: Decimal = Decimal("3")
    score_cap_pt: Decimal = Decimal("10")


@dataclass(frozen=True)
class RiskResult:
    risk_level: str
    decided_by: str
    worst_line_excess_pt: Decimal
    worst_line: str | None
    blended_excess_pt: Decimal
    blended_score: Decimal
    violating_line_count: int
    total_excess_value: Decimal
    lines: list[ScoredLine] = field(default_factory=list)


def _level(value: Decimal, medium_at: Decimal, high_at: Decimal) -> str:
    if value >= high_at:
        return RiskLevel.HIGH
    if value >= medium_at:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _q2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def blended_util_score_quotation(
    lines: list[dict], thresholds: RiskThresholds | None = None
) -> RiskResult:
    """Score a quotation.

    `lines` carries dicts of product, qty, unit_price, discount_pct and
    allowed_pct. allowed_pct is min(tier, category), resolved before this runs.
    """
    cfg = thresholds or RiskThresholds()

    scored: list[ScoredLine] = []
    total_excess_value = _ZERO
    quote_list_value = _ZERO

    for line in lines:
        # List value, never net. A net denominator shrinks as discounts grow, so
        # the same violation would score higher on a more discounted quote.
        list_value = Decimal(str(line["unit_price"])) * Decimal(str(line["qty"]))
        excess_pt = max(
            _ZERO,
            Decimal(str(line["discount_pct"])) - Decimal(str(line["allowed_pct"])),
        )
        excess_value = list_value * excess_pt / Decimal("100")

        quote_list_value += list_value
        total_excess_value += excess_value
        scored.append(
            ScoredLine(
                product=line.get("product", ""),
                list_value=list_value,
                excess_pt=excess_pt,
                excess_value=excess_value,
            )
        )

    worst = max(scored, key=lambda s: s.excess_pt, default=None)
    worst_pt = worst.excess_pt if worst else _ZERO

    # "Taken as a whole, this order is N percentage points over policy." Same
    # unit as the line excess, so both thresholds mean the same thing.
    blended_pt = (
        total_excess_value / quote_list_value * Decimal("100")
        if quote_list_value
        else _ZERO
    )

    worst_level = _level(worst_pt, cfg.worst_medium_pt, cfg.worst_high_pt)
    blended_level = _level(blended_pt, cfg.blended_medium_pt, cfg.blended_high_pt)

    # PS section 4 A3: route to the HIGHEST required level.
    risk_level = max(worst_level, blended_level, key=lambda lv: _ORDER[lv])

    if risk_level == RiskLevel.LOW:
        decided_by = DecidedBy.NONE
    elif _ORDER[worst_level] > _ORDER[blended_level]:
        decided_by = DecidedBy.WORST_LINE
    elif _ORDER[blended_level] > _ORDER[worst_level]:
        decided_by = DecidedBy.BLENDED
    else:
        decided_by = DecidedBy.BOTH

    return RiskResult(
        risk_level=risk_level,
        decided_by=decided_by,
        worst_line_excess_pt=_q2(worst_pt),
        worst_line=worst.product if worst and worst.excess_pt > 0 else None,
        blended_excess_pt=_q2(blended_pt),
        blended_score=min(Decimal("1"), blended_pt / cfg.score_cap_pt).quantize(
            Decimal("0.001"), rounding=ROUND_HALF_UP
        ),
        violating_line_count=sum(1 for s in scored if s.excess_pt > 0),
        total_excess_value=_q2(total_excess_value),
        lines=scored,
    )
