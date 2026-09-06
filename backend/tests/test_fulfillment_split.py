"""The warehouse split algorithm.

Specification is docs/engineering/warehouse-split.md. These run without HTTP or
a database, so they pin the objective directly: fewest shipments first, then
lowest weighted cost.
"""

from decimal import Decimal

from app.utils.fulfillment import (
    SHIPMENT_BASE_COST,
    WarehouseStock,
    fulfillment_util_split,
)

LAPTOP, DOCK = 10, 20


def wh(id_, name, weight, available):
    return WarehouseStock(id_, name, Decimal(str(weight)), available)


class TestFewestShipmentsFirst:
    def test_one_warehouse_that_can_cover_everything_is_used_alone(self) -> None:
        plan = fulfillment_util_split(
            {LAPTOP: 10},
            [wh(1, "Main", 1.0, {LAPTOP: 40}), wh(2, "East", 1.4, {LAPTOP: 40})],
        )

        assert plan.shipments == 1
        assert plan.is_complete

    def test_among_warehouses_that_can_cover_it_the_cheapest_wins(self) -> None:
        plan = fulfillment_util_split(
            {LAPTOP: 10},
            [wh(1, "Dear", 3.0, {LAPTOP: 40}), wh(2, "Cheap", 1.0, {LAPTOP: 40})],
        )

        assert [a.warehouse_id for a in plan.allocations] == [2]
        assert plan.total_cost == SHIPMENT_BASE_COST * Decimal("1.0")

    def test_a_large_dear_warehouse_beats_a_small_cheap_one(self) -> None:
        """The point of A4.

        Cheapest-first would take the two-unit depot before the forty-unit one
        and produce an extra box - optimising cost at the expense of shipments,
        which is backwards.
        """
        plan = fulfillment_util_split(
            {LAPTOP: 40},
            [
                wh(1, "Tiny Cheap", 1.0, {LAPTOP: 2}),
                wh(2, "Big Dear", 5.0, {LAPTOP: 40}),
            ],
        )

        assert plan.shipments == 1
        assert [a.warehouse_id for a in plan.allocations] == [2]


class TestSplitting:
    def test_the_worked_example_from_the_spec(self) -> None:
        """24 laptops; Main has 22 free, East has 4."""
        plan = fulfillment_util_split(
            {LAPTOP: 24},
            [
                wh(1, "Main Warehouse", 1.0, {LAPTOP: 22}),
                wh(2, "East Depot", 1.4, {LAPTOP: 4}),
            ],
        )

        assert plan.shipments == 2
        assert plan.is_complete
        assert plan.total_cost == SHIPMENT_BASE_COST * Decimal("2.4")
        assert sorted(a.qty for a in plan.allocations) == [2, 22]

    def test_a_multi_product_order_ships_one_box_per_warehouse(self) -> None:
        """Shipment count is distinct warehouses, not lines."""
        plan = fulfillment_util_split(
            {LAPTOP: 5, DOCK: 5},
            [wh(1, "Main", 1.0, {LAPTOP: 5, DOCK: 5})],
        )

        assert len(plan.allocations) == 2
        assert plan.shipments == 1


class TestBackorders:
    def test_uncoverable_demand_becomes_a_backorder_row(self) -> None:
        plan = fulfillment_util_split(
            {LAPTOP: 30},
            [wh(1, "Main", 1.0, {LAPTOP: 22}), wh(2, "East", 1.4, {LAPTOP: 4})],
        )

        backorders = [a for a in plan.allocations if a.warehouse_id is None]
        assert len(backorders) == 1
        assert backorders[0].qty == 4
        assert plan.backordered == 4
        assert not plan.is_complete

    def test_no_stock_anywhere_backorders_the_whole_order(self) -> None:
        plan = fulfillment_util_split({LAPTOP: 10}, [wh(1, "Main", 1.0, {LAPTOP: 0})])

        assert plan.shipments == 0
        assert plan.backordered == 10

    def test_no_warehouses_at_all_backorders_rather_than_crashing(self) -> None:
        plan = fulfillment_util_split({LAPTOP: 3}, [])
        assert plan.backordered == 3


class TestDeterminism:
    def test_a_tie_on_coverage_breaks_on_weight(self) -> None:
        plan = fulfillment_util_split(
            {LAPTOP: 5},
            [wh(1, "A", 2.0, {LAPTOP: 5}), wh(2, "B", 1.0, {LAPTOP: 5})],
        )
        assert [a.warehouse_id for a in plan.allocations] == [2]

    def test_the_same_input_always_produces_the_same_split(self) -> None:
        """A demo that differs between runs is not showing an algorithm."""
        stock = [
            wh(1, "Main", 1.0, {LAPTOP: 10}),
            wh(2, "East", 1.0, {LAPTOP: 10}),
            wh(3, "West", 1.0, {LAPTOP: 10}),
        ]
        runs = [
            [
                (a.warehouse_id, a.qty)
                for a in fulfillment_util_split({LAPTOP: 25}, stock).allocations
            ]
            for _ in range(5)
        ]
        assert all(run == runs[0] for run in runs)


class TestEmptyInput:
    def test_an_empty_order_plans_nothing(self) -> None:
        plan = fulfillment_util_split({}, [wh(1, "Main", 1.0, {LAPTOP: 10})])
        assert plan.allocations == []
        assert plan.shipments == 0
        assert plan.is_complete
