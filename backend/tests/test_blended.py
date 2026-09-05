"""The blended discount risk engine.

These six scenarios are the specification, not illustrations of it. They come
from risk-engine-and-ml.md 3.7 and run without HTTP or a database, so they are
also the fastest answer to "is the routing real?".
"""

from decimal import Decimal

from app.utils.blended import blended_util_score_quotation
from app.utils.discount import discount_util_excess_pt, discount_util_resolve_limit


def line(product, qty, unit_price, discount_pct, allowed_pct):
    return {
        "product": product,
        "qty": qty,
        "unit_price": unit_price,
        "discount_pct": discount_pct,
        "allowed_pct": allowed_pct,
    }


class TestTheSixScenarios:
    def test_one_severe_line_flags_the_whole_quotation(self) -> None:
        """PS section 10's headline example, and the wireframe's Q-1042.

        A $450 service line 8pt over is 15% of a $3,030 quotation. The blended
        figure alone is 1.19pt, which would route LOW - so the worst-line path
        has to be what decides.
        """
        result = blended_util_score_quotation(
            [
                line("Laptop Pro 14", 2, 1200, 12, 15),
                line("Onsite Setup Service", 1, 450, 18, 10),
                line("Extended Warranty", 1, 180, 10, 15),
            ]
        )

        assert result.risk_level == "HIGH"
        assert result.decided_by == "WORST_LINE"
        assert result.worst_line_excess_pt == Decimal("8.00")
        assert result.blended_excess_pt == Decimal("1.19")
        assert result.worst_line == "Onsite Setup Service"

    def test_several_small_violations_are_caught_together(self) -> None:
        """PS section 10's "why blended": 2pt, 3pt and 2pt across equal lines."""
        result = blended_util_score_quotation(
            [
                line("A", 1, 1000, 12, 10),
                line("B", 1, 1000, 13, 10),
                line("C", 1, 1000, 12, 10),
            ]
        )

        assert result.risk_level == "MEDIUM"
        assert result.decided_by == "BOTH"
        assert result.violating_line_count == 3

    def test_death_by_a_thousand_cuts_escalates_on_the_blended_path(self) -> None:
        """Why the aggregate is not redundant.

        No line reaches the 5pt HIGH cutoff, so the worst-line path says MEDIUM.
        But $200 of margin has quietly gone, and that must reach Finance.
        """
        result = blended_util_score_quotation(
            [line(f"L{i}", 1, 1000, 14, 10) for i in range(5)]
        )

        assert result.risk_level == "HIGH"
        assert result.decided_by == "BLENDED"
        assert result.total_excess_value == Decimal("200.00")

    def test_a_compliant_quotation_needs_no_approval(self) -> None:
        result = blended_util_score_quotation(
            [line("Laptop", 2, 1200, 12, 15), line("Warranty", 1, 180, 10, 15)]
        )

        assert result.risk_level == "LOW"
        assert result.decided_by == "NONE"
        assert result.violating_line_count == 0
        assert result.worst_line is None

    def test_even_a_trivial_violation_needs_a_manager(self) -> None:
        """1pt over on a $20 cable. Small, but it is still over its ceiling."""
        result = blended_util_score_quotation(
            [line("Laptop", 5, 1200, 12, 15), line("Cable", 1, 20, 11, 10)]
        )

        assert result.risk_level == "MEDIUM"
        assert result.decided_by == "WORST_LINE"

    def test_a_severe_line_cannot_hide_inside_a_large_clean_order(self) -> None:
        """The dilution case that killed the original single-formula design.

        15pt over, but the blended figure is 0.11 - effectively invisible.
        """
        result = blended_util_score_quotation(
            [line("Bulk Laptops", 50, 1200, 10, 15), line("Setup", 1, 450, 25, 10)]
        )

        assert result.risk_level == "HIGH"
        assert result.decided_by == "WORST_LINE"
        assert result.worst_line_excess_pt == Decimal("15.00")
        assert result.blended_excess_pt == Decimal("0.11")


class TestEdgeCases:
    def test_an_empty_quotation_does_not_divide_by_zero(self) -> None:
        result = blended_util_score_quotation([])
        assert result.risk_level == "LOW"
        assert result.blended_excess_pt == Decimal("0.00")

    def test_the_display_score_stays_within_zero_and_one(self) -> None:
        """The earlier draft returned an unbounded number described as 0-1."""
        result = blended_util_score_quotation([line("Giveaway", 1, 1000, 90, 5)])
        assert Decimal("0") <= result.blended_score <= Decimal("1")

    def test_a_discount_under_the_ceiling_never_offsets_one_over(self) -> None:
        """Otherwise a deep discount could be hidden behind an undiscounted line."""
        result = blended_util_score_quotation(
            [line("Under", 1, 1000, 0, 15), line("Over", 1, 1000, 20, 10)]
        )
        assert result.violating_line_count == 1
        assert result.total_excess_value == Decimal("100.00")


class TestLimitResolution:
    def test_the_stricter_of_tier_and_category_wins(self) -> None:
        """Gold allows 15, Services caps at 10, so the line is held to 10."""
        assert discount_util_resolve_limit(Decimal("15"), Decimal("10")) == Decimal(
            "10"
        )

    def test_excess_is_never_negative(self) -> None:
        assert discount_util_excess_pt(Decimal("8"), Decimal("15")) == Decimal("0")

    def test_the_ps_worked_example_resolves_to_eight_points_over(self) -> None:
        allowed = discount_util_resolve_limit(Decimal("15"), Decimal("10"))
        assert discount_util_excess_pt(Decimal("18"), allowed) == Decimal("8")
