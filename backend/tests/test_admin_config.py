"""Backend configuration.

PS section 9 step 1 is the first thing a judge does: sign in and set up a
discount tier, a warehouse and a subscription plan.
"""

from fastapi.testclient import TestClient

ADMIN = {"email": "admin@dealflow360.com", "password": "dealflow123"}
REP = {"email": "rep@dealflow360.com", "password": "dealflow123"}


def sign_in(client: TestClient, who: dict) -> TestClient:
    client.post("/auth/login", json=who)
    return client


class TestStepOne:
    def test_an_admin_can_add_a_discount_tier(self, client: TestClient) -> None:
        admin = sign_in(client, ADMIN)

        data = admin.put(
            "/admin/discount-config",
            json={
                "tier_ceilings": [{"tier": "Platinum", "max_discount": 20}],
                "category_ceilings": [],
            },
        ).json()["data"]

        assert "Platinum" in {t["tier"] for t in data["tier_ceilings"]}

    def test_an_admin_can_add_a_warehouse(self, client: TestClient) -> None:
        admin = sign_in(client, ADMIN)

        data = admin.put(
            "/admin/warehouses",
            json={
                "warehouses": [
                    {
                        "name": "North Hub",
                        "region": "US-North",
                        "shipping_cost_weight": 1.2,
                        "active": True,
                    }
                ]
            },
        ).json()["data"]

        assert "North Hub" in {w["name"] for w in data}

    def test_an_admin_can_add_a_subscription_plan(self, client: TestClient) -> None:
        admin = sign_in(client, ADMIN)

        data = admin.put(
            "/admin/subscription-plans",
            json={
                "plans": [
                    {
                        "name": "Care Plan 3yr",
                        "cycle": "Monthly",
                        "price": 62,
                        "proration_enabled": True,
                    }
                ]
            },
        ).json()["data"]

        assert "Care Plan 3yr" in {p["name"] for p in data}


class TestPermissions:
    def test_a_rep_may_read_the_ceilings_they_work_against(
        self, client: TestClient
    ) -> None:
        assert sign_in(client, REP).get("/admin/discount-config").status_code == 200

    def test_a_rep_may_not_change_them(self, client: TestClient) -> None:
        res = sign_in(client, REP).put(
            "/admin/discount-config",
            json={"tier_ceilings": [], "category_ceilings": []},
        )
        assert res.status_code == 403

    def test_a_customer_cannot_read_configuration(self, client: TestClient) -> None:
        client.post(
            "/auth/login",
            json={"email": "customer@acmecorp.com", "password": "dealflow123"},
        )
        assert client.get("/admin/warehouses").status_code == 403


class TestConfigurationDrivesTheEngine:
    def test_the_routing_table_is_derived_from_the_actual_chain(
        self, client: TestClient
    ) -> None:
        """Screen 18's third table is generated, so it cannot describe a chain
        the engine does not use."""
        data = sign_in(client, ADMIN).get("/admin/discount-config").json()["data"]

        rules = {r["range"]: r["approval"] for r in data["routing_rules"]}
        assert any("Sales Manager then Finance" == v for v in rules.values())

    def test_raising_a_category_ceiling_changes_the_routing(
        self, client: TestClient
    ) -> None:
        """The proof that the tables drive the engine rather than decorate it.

        Q-1042's service line is 18% against a 10% ceiling. Raise the ceiling to
        20% and the same quotation stops needing approval.
        """
        rep = sign_in(client, REP)
        assert rep.post("/quotations/q1/submit").json()["data"]["risk_level"] == "HIGH"

        sign_in(client, ADMIN).put(
            "/admin/discount-config",
            json={
                "tier_ceilings": [{"tier": "Gold", "max_discount": 20}],
                "category_ceilings": [{"category": "Services", "max_discount": 20}],
            },
        )

        after = sign_in(client, REP).post("/quotations/q1/submit").json()["data"]
        assert after["risk_level"] == "LOW"
        assert after["required_approval"] == []


class TestDashboard:
    def test_the_at_risk_count_does_not_depend_on_visiting_deal_health(
        self, client: TestClient
    ) -> None:
        """Counting stored flags would read zero until the board was opened."""
        data = sign_in(client, REP).get("/dashboard/summary").json()["data"]
        assert data["at_risk_deals"] > 0

    def test_activity_comes_from_the_audit_trail(self, client: TestClient) -> None:
        rep = sign_in(client, REP)
        rep.post("/quotations/q1/submit")

        activity = rep.get("/dashboard/summary").json()["data"]["recent_activity"]

        assert activity
        assert any("submitted for approval" in row["text"] for row in activity)


class TestProducts:
    def test_the_catalogue_lists_products(self, client: TestClient) -> None:
        rows = sign_in(client, REP).get("/products").json()["data"]
        assert rows

    def test_a_product_carries_its_cost_so_margin_is_computable(
        self, client: TestClient
    ) -> None:
        data = sign_in(client, REP).get("/products/p1").json()["data"]
        assert data["cost_price"] > 0
        assert data["price"] > data["cost_price"]

    def test_an_unknown_product_is_not_found(self, client: TestClient) -> None:
        assert sign_in(client, REP).get("/products/p9999").status_code == 404


class TestWhereStockIs:
    def test_a_product_reports_stock_per_warehouse(self, client: TestClient) -> None:
        """qty_on_hand is one number that cannot answer "can this ship from a
        single warehouse", which is the question the split logic settles."""
        data = sign_in(client, ADMIN).get("/products/p1").json()["data"]

        assert data["stock"], "Laptop Pro 14 is stocked in the seed"
        for row in data["stock"]:
            assert row["warehouse"]
            assert row["available"] == row["on_hand"] - row["reserved"]

        # Only depots the split logic will actually use count as promisable.
        assert data["total_available"] == sum(
            r["available"] for r in data["stock"] if r["active"]
        )

    def test_an_inactive_warehouse_is_listed_but_not_counted(
        self, client: TestClient
    ) -> None:
        """Hiding it would make the totals look wrong; counting it would promise
        stock the split will never draw on."""
        data = sign_in(client, ADMIN).get("/products/p1").json()["data"]

        inactive = [r for r in data["stock"] if not r["active"]]
        assert inactive, "the seed keeps EU Transit Hub inactive"
        assert all(r["available"] > 0 for r in inactive)
        assert data["total_available"] < sum(r["available"] for r in data["stock"])

    def test_warehouses_report_what_they_hold(self, client: TestClient) -> None:
        rows = sign_in(client, ADMIN).get("/admin/warehouses").json()["data"]

        stocked = [w for w in rows if w["product_lines"] > 0]
        assert stocked
        for w in stocked:
            assert w["units_available"] == w["units_on_hand"] - w["units_reserved"]
            assert w["below_reorder"] <= w["product_lines"]


class TestAddingToTheCatalogue:
    def test_an_admin_can_add_a_product(self, client: TestClient) -> None:
        admin = sign_in(client, ADMIN)
        before = len(admin.get("/products").json()["data"])

        res = admin.post(
            "/products",
            json={
                "name": "Barcode Scanner Pro",
                "category": "Hardware",
                "unit_price": 290,
                "cost_price": 155,
                "unit": "Each",
                "tax_pct": 8,
                "description": "Handheld 2D scanner",
                "is_subscription": False,
                "recurring_cycle": None,
            },
        )

        assert res.status_code == 201
        assert res.json()["data"]["name"] == "Barcode Scanner Pro"
        assert len(admin.get("/products").json()["data"]) == before + 1

    def test_a_new_product_is_stocked_nowhere_yet(self, client: TestClient) -> None:
        """A product exists before it sits anywhere - the screen has to say so
        rather than showing an empty table that reads as a failure."""
        admin = sign_in(client, ADMIN)
        created = admin.post(
            "/products",
            json={
                "name": "Cable Tester",
                "category": "Hardware",
                "unit_price": 90,
                "cost_price": 40,
                "unit": "Each",
                "tax_pct": 8,
                "description": None,
                "is_subscription": False,
                "recurring_cycle": None,
            },
        ).json()["data"]

        assert created["stock"] == []
        assert created["total_available"] == 0

    def test_a_rep_cannot_add_a_product(self, client: TestClient) -> None:
        res = sign_in(client, REP).post(
            "/products",
            json={
                "name": "Nope",
                "category": "Hardware",
                "unit_price": 1,
                "cost_price": 0,
                "unit": "Each",
                "tax_pct": 0,
                "description": None,
                "is_subscription": False,
                "recurring_cycle": None,
            },
        )

        assert res.status_code == 403

    def test_a_cost_above_the_price_is_refused_on_create_too(
        self, client: TestClient
    ) -> None:
        res = sign_in(client, ADMIN).post(
            "/products",
            json={
                "name": "Loss Leader",
                "category": "Hardware",
                "unit_price": 10,
                "cost_price": 99,
                "unit": "Each",
                "tax_pct": 0,
                "description": None,
                "is_subscription": False,
                "recurring_cycle": None,
            },
        )

        assert res.status_code == 422
