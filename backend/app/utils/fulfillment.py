"""The warehouse split algorithm.

Specified in docs/engineering/warehouse-split.md. Objective is ordered, not
blended: fewest shipments first, then lowest weighted cost - PS section 4 A4.

No FastAPI imports.
"""

from dataclasses import dataclass, field
from decimal import Decimal

# Cost of one box before the warehouse's weighting is applied.
SHIPMENT_BASE_COST = Decimal("25.00")


@dataclass(frozen=True)
class WarehouseStock:
    """Availability at one warehouse, as the algorithm sees it."""

    warehouse_id: int
    name: str
    shipping_cost_weight: Decimal
    available: dict[int, int]  # product_id -> units free to allocate


@dataclass
class Allocation:
    product_id: int
    warehouse_id: int | None  # None means backorder
    qty: int


@dataclass
class SplitPlan:
    allocations: list[Allocation] = field(default_factory=list)
    shipments: int = 0
    total_cost: Decimal = Decimal("0")
    backordered: int = 0

    @property
    def is_complete(self) -> bool:
        return self.backordered == 0


def _covers(stock: WarehouseStock, demand: dict[int, int]) -> int:
    """How many outstanding units this warehouse could supply."""
    return sum(min(qty, stock.available.get(pid, 0)) for pid, qty in demand.items())


def _can_cover_everything(stock: WarehouseStock, demand: dict[int, int]) -> bool:
    return all(stock.available.get(pid, 0) >= qty for pid, qty in demand.items())


def fulfillment_util_split(
    demand: dict[int, int], warehouses: list[WarehouseStock]
) -> SplitPlan:
    """Plan how to ship `demand` from the warehouses that hold stock.

    `demand` maps product_id to units required. Warehouses are assumed already
    filtered to active ones.
    """
    plan = SplitPlan()
    remaining = {pid: qty for pid, qty in demand.items() if qty > 0}
    if not remaining:
        return plan

    # Deterministic ordering. A split that differs between runs is not
    # demonstrating an algorithm.
    ordered = sorted(warehouses, key=lambda w: (w.shipping_cost_weight, w.name))

    # Step 1: one shipment beats every multi-warehouse answer, so look for a
    # single warehouse holding the whole order before considering combinations.
    single = next((w for w in ordered if _can_cover_everything(w, remaining)), None)
    if single is not None:
        for pid, qty in remaining.items():
            plan.allocations.append(Allocation(pid, single.warehouse_id, qty))
        plan.shipments = 1
        plan.total_cost = SHIPMENT_BASE_COST * single.shipping_cost_weight
        return plan

    # Step 2: greedy cover. Take the warehouse that clears the most outstanding
    # demand, not the cheapest - cheapest-first optimises the secondary
    # objective and produces more boxes, which is what A4 says to avoid.
    used: list[WarehouseStock] = []
    pool = {w.warehouse_id: dict(w.available) for w in ordered}

    while any(qty > 0 for qty in remaining.values()):
        best = max(
            ordered,
            key=lambda w: (
                _covers(
                    WarehouseStock(
                        w.warehouse_id,
                        w.name,
                        w.shipping_cost_weight,
                        pool[w.warehouse_id],
                    ),
                    remaining,
                ),
                -float(w.shipping_cost_weight),
            ),
            default=None,
        )
        if best is None:
            break

        supplied = 0
        for pid, qty in list(remaining.items()):
            take = min(qty, pool[best.warehouse_id].get(pid, 0))
            if take <= 0:
                continue
            plan.allocations.append(Allocation(pid, best.warehouse_id, take))
            pool[best.warehouse_id][pid] -= take
            remaining[pid] -= take
            supplied += take

        if supplied == 0:
            # Nothing left anywhere can help; the rest is a backorder.
            break

        used.append(best)

    # Step 3: whatever is still outstanding could not be covered.
    for pid, qty in remaining.items():
        if qty > 0:
            plan.allocations.append(Allocation(pid, None, qty))
            plan.backordered += qty

    plan.shipments = len(used)
    plan.total_cost = sum(
        (SHIPMENT_BASE_COST * w.shipping_cost_weight for w in used), Decimal("0")
    )
    return plan


def fulfillment_util_shipment_cost(weight: Decimal) -> Decimal:
    return SHIPMENT_BASE_COST * weight
