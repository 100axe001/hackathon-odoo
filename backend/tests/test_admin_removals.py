"""Removing configuration that other records still point at.

Each of these refuses rather than cascading: a silent cascade would leave real
records - customers, subscriptions, fulfilled orders - pointing at a row that
no longer exists.
"""

from fastapi.testclient import TestClient

ADMIN = {"email": "admin@dealflow360.com", "password": "dealflow123"}
REP = {"email": "rep@dealflow360.com", "password": "dealflow123"}
MANAGER = {"email": "manager@dealflow360.com", "password": "dealflow123"}
FINANCE = {"email": "finance@dealflow360.com", "password": "dealflow123"}


def sign_in(client: TestClient, who: dict) -> TestClient:
    client.post("/auth/login", json=who)
    return client


class TestTiers:
    def test_a_new_tier_can_be_added_and_drives_the_engine(
        self, client: TestClient
    ) -> None:
        admin = sign_in(client, ADMIN)
        current = admin.get("/admin/discount-config").json()["data"]

        res = admin.put(
            "/admin/discount-config",
            json={
                "tier_ceilings": current["tier_ceilings"]
                + [{"tier": "Platinum", "max_discount": 20}],
                "category_ceilings": current["category_ceilings"],
            },
        )

        assert res.status_code == 200
        names = [t["tier"] for t in res.json()["data"]["tier_ceilings"]]
        assert "Platinum" in names

    def test_a_tier_customers_are_on_cannot_be_removed(
        self, client: TestClient
    ) -> None:
        res = sign_in(client, ADMIN).delete("/admin/discount-tiers/Gold")

        assert res.status_code == 409
        assert "customer" in res.json()["detail"]["message"]
        tiers = client.get("/admin/discount-config").json()["data"]["tier_ceilings"]
        assert "Gold" in [t["tier"] for t in tiers]

    def test_an_unused_tier_can_be_removed(self, client: TestClient) -> None:
        admin = sign_in(client, ADMIN)
        current = admin.get("/admin/discount-config").json()["data"]
        admin.put(
            "/admin/discount-config",
            json={
                "tier_ceilings": current["tier_ceilings"]
                + [{"tier": "Platinum", "max_discount": 20}],
                "category_ceilings": current["category_ceilings"],
            },
        )

        res = admin.delete("/admin/discount-tiers/Platinum")

        assert res.status_code == 200
        assert "Platinum" not in [
            t["tier"] for t in res.json()["data"]["tier_ceilings"]
        ]


class TestWarehouses:
    def test_a_warehouse_that_has_shipped_cannot_be_removed(
        self, client: TestClient
    ) -> None:
        """The split has to keep resolving for orders already fulfilled."""
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

        admin = sign_in(client, ADMIN)
        used = admin.get("/admin/warehouses").json()["data"][0]
        res = admin.delete(f"/admin/warehouses/{used['id']}")

        assert res.status_code == 409
        assert "fulfilled" in res.json()["detail"]["message"]

    def test_an_unused_warehouse_goes_with_its_stock(self, client: TestClient) -> None:
        admin = sign_in(client, ADMIN)
        before = admin.get("/admin/warehouses").json()["data"]
        spare = next(w for w in before if w["name"] == "South Hub")

        res = admin.delete(f"/admin/warehouses/{spare['id']}")

        assert res.status_code == 200
        assert len(res.json()["data"]) == len(before) - 1


class TestPlans:
    def test_a_plan_with_subscribers_cannot_be_removed(
        self, client: TestClient
    ) -> None:
        admin = sign_in(client, ADMIN)
        subscribed = next(
            p
            for p in admin.get("/admin/subscription-plans").json()["data"]
            if p["name"] == "Care Plan 2yr"
        )

        res = admin.delete(f"/admin/subscription-plans/{subscribed['id']}")

        assert res.status_code == 409
        assert "subscription" in res.json()["detail"]["message"]

    def test_only_an_admin_may_remove_configuration(self, client: TestClient) -> None:
        """Reading configuration is open to internal roles; changing it is not."""
        plans = sign_in(client, ADMIN).get("/admin/subscription-plans").json()["data"]

        res = sign_in(client, REP).delete(f"/admin/subscription-plans/{plans[0]['id']}")

        assert res.status_code == 403
