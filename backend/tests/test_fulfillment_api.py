"""Fulfillment over HTTP: stock, the split, accepting, overriding, backorders.

test_fulfillment_split.py proves the algorithm. This proves reserving, the
backorder path, and that a split holds nothing until it is accepted.
"""

from fastapi.testclient import TestClient

FINANCE = {"email": "finance@dealflow360.com", "password": "dealflow123"}
REP = {"email": "rep@dealflow360.com", "password": "dealflow123"}
MANAGER = {"email": "manager@dealflow360.com", "password": "dealflow123"}


def sign_in(client: TestClient, who: dict) -> TestClient:
    client.post("/auth/login", json=who)
    return client


def stock_for(client: TestClient, warehouse: str, product: str) -> dict:
    rows = client.get("/fulfillment/stock").json()["data"]
    return next(
        r for r in rows if r["warehouse"] == warehouse and r["product"] == product
    )


class TestStock:
    def test_available_is_on_hand_minus_reserved(self, client: TestClient) -> None:
        sign_in(client, FINANCE)
        row = stock_for(client, "East Depot", "Laptop Pro 14")

        assert row["available"] == row["in_stock"] - row["reserved"]

    def test_a_customer_cannot_see_stock(self, client: TestClient) -> None:
        client.post(
            "/auth/login",
            json={"email": "customer@acmecorp.com", "password": "dealflow123"},
        )
        assert client.get("/fulfillment/stock").status_code == 403


class TestSuggestedSplit:
    def test_an_order_that_one_warehouse_cannot_cover_is_split(
        self, client: TestClient
    ) -> None:
        """Main holds one free laptop and the order needs two."""
        sign_in(client, FINANCE)
        data = client.get("/quotations/q1/fulfillment-split").json()["data"]

        assert data["total_shipments"] == 2
        assert data["complete"] is True

    def test_shipping_cost_is_charged_once_per_warehouse(
        self, client: TestClient
    ) -> None:
        """A box carries every line from that warehouse, not one box per line."""
        sign_in(client, FINANCE)
        data = client.get("/quotations/q1/fulfillment-split").json()["data"]

        charged = [row for row in data["warehouses"] if row["cost"] > 0]
        assert len(charged) == data["total_shipments"]

    def test_suggesting_reserves_nothing(self, client: TestClient) -> None:
        """Merely looking at a quotation must not take stock out of circulation."""
        fin = sign_in(client, FINANCE)
        before = stock_for(fin, "East Depot", "Laptop Pro 14")["reserved"]

        fin.get("/quotations/q1/fulfillment-split")

        assert stock_for(fin, "East Depot", "Laptop Pro 14")["reserved"] == before


class TestAccepting:
    def test_accepting_reserves_the_stock_it_uses(self, client: TestClient) -> None:
        fin = sign_in(client, FINANCE)
        before = stock_for(fin, "East Depot", "Laptop Pro 14")["reserved"]

        fin.get("/quotations/q1/fulfillment-split")
        fin.post("/quotations/q1/fulfillment/accept")

        assert stock_for(fin, "East Depot", "Laptop Pro 14")["reserved"] > before

    def test_an_unsplit_order_says_so(self, client: TestClient) -> None:
        """Reads the label for one unsplit order rather than asserting every
        order is unsplit - the seed now also carries one already accepted."""
        fin = sign_in(client, FINANCE)

        rows = fin.get("/fulfillment/orders").json()["data"]

        assert rows
        unsplit = next(r for r in rows if r["warehouses"] == "Not yet split")
        assert unsplit["status"] == "Awaiting split"

    def test_a_split_order_lists_the_warehouses_it_uses(
        self, client: TestClient
    ) -> None:
        fin = sign_in(client, FINANCE)
        fin.get("/quotations/q4/fulfillment-split")
        fin.post("/quotations/q4/fulfillment/accept")

        row = next(
            r
            for r in fin.get("/fulfillment/orders").json()["data"]
            if r["order"] == "Q-1030"
        )
        assert row["warehouses"] != "Not yet split"

    def test_an_unknown_quotation_is_not_found(self, client: TestClient) -> None:
        sign_in(client, FINANCE)
        assert client.get("/quotations/q9999/fulfillment-split").status_code == 404


class TestOverride:
    def test_a_manual_split_replaces_the_suggestion(self, client: TestClient) -> None:
        fin = sign_in(client, FINANCE)
        fin.get("/quotations/q1/fulfillment-split")

        data = fin.post(
            "/quotations/q1/fulfillment/override",
            json={"allocations": [{"warehouse_id": 2, "product_id": 1, "qty": 2}]},
        ).json()["data"]

        assert data["status"] == "OVERRIDDEN"
        assert data["total_shipments"] == 1

    def test_overriding_releases_what_the_previous_plan_reserved(
        self, client: TestClient
    ) -> None:
        """Otherwise the old reservation leaks and never comes back.

        The split uses East for one laptop; moving the whole order onto Main has
        to hand East's unit back.
        """
        fin = sign_in(client, FINANCE)
        fin.get("/quotations/q1/fulfillment-split")
        fin.post("/quotations/q1/fulfillment/accept")
        after_accept = stock_for(fin, "East Depot", "Laptop Pro 14")["reserved"]

        fin.post(
            "/quotations/q1/fulfillment/override",
            json={"allocations": [{"warehouse_id": 1, "product_id": 1, "qty": 2}]},
        )

        assert stock_for(fin, "East Depot", "Laptop Pro 14")["reserved"] < after_accept


class TestBackorderAndRestock:
    def test_stock_that_cannot_be_covered_is_backordered(
        self, client: TestClient
    ) -> None:
        """Q-1030 wants eight laptops; five are available across active depots."""
        fin = sign_in(client, FINANCE)

        data = fin.get("/quotations/q4/fulfillment-split").json()["data"]

        assert data["backordered"] > 0
        assert data["complete"] is False
        assert any(r["warehouse"] == "Backorder" for r in data["warehouses"])

    def test_restocking_lets_the_backorder_be_consolidated(
        self, client: TestClient
    ) -> None:
        """PS 4 B6: the prompt appears once stock arrives."""
        fin = sign_in(client, FINANCE)
        assert (
            fin.get("/quotations/q4/fulfillment-split").json()["data"]["complete"]
            is False
        )

        fin.post(
            "/fulfillment/restock",
            json={"warehouse_id": 1, "product_id": 1, "qty": 100},
        )

        after = fin.get("/quotations/q4/fulfillment-split").json()["data"]
        assert after["complete"] is True
        assert after["backordered"] == 0


class TestReservationOwnership:
    def test_reserved_stock_names_the_company_holding_it(
        self, client: TestClient
    ) -> None:
        """A reserved figure on its own says stock is spoken for but not by whom,
        which is the question anyone working a shipping desk actually has."""
        sign_in(client, REP).post("/quotations/q1/submit")
        sign_in(client, MANAGER).post(
            "/quotations/q1/approve", json={"decision": "approve"}
        )
        sign_in(client, FINANCE).post(
            "/quotations/q1/approve", json={"decision": "approve"}
        )
        rep = sign_in(client, REP)
        rep.get("/quotations/q1/fulfillment-split")
        rep.post("/quotations/q1/fulfillment/accept")

        rows = rep.get("/fulfillment/stock").json()["data"]
        claimed = [r for r in rows if r["reserved_for"]]

        assert claimed, "accepting a split must attribute the stock it reserved"
        for row in claimed:
            for claim in row["reserved_for"]:
                assert claim["customer"]
                assert claim["quotation"].startswith("Q-")
                assert claim["qty"] > 0

        assert any(
            claim["quotation"] == "Q-1042"
            for row in claimed
            for claim in row["reserved_for"]
        )

    def test_untouched_stock_is_attributed_to_nobody(self, client: TestClient) -> None:
        """Seeded reservations have no allocation behind them, so the column has
        to be honest about that rather than inventing an owner."""
        rows = sign_in(client, REP).get("/fulfillment/stock").json()["data"]

        assert any(row["reserved_for"] == [] for row in rows)
