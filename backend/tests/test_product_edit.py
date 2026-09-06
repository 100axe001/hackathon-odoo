"""Editing the catalogue.

Screen 17's Save button used to be decorative. These cover the endpoint behind
it: who may press it, what it persists, and the one edit it must refuse.
"""

from fastapi.testclient import TestClient

ADMIN = {"email": "admin@dealflow360.com", "password": "dealflow123"}
REP = {"email": "rep@dealflow360.com", "password": "dealflow123"}

# p1 is the seeded "Laptop Pro 14" at 1200 list against a 780 cost.
PRODUCT = "/products/p1"


def sign_in(client: TestClient, who: dict) -> TestClient:
    client.post("/auth/login", json=who)
    return client


def edit(**overrides: object) -> dict:
    """A complete payload, since the PUT replaces every editable field."""
    body = {
        "name": "Laptop Pro 14",
        "category": "Hardware",
        "unit_price": 1200,
        "cost_price": 780,
        "unit": "Each",
        "tax_pct": 8,
        "description": "Fourteen-inch workstation laptop.",
        "is_subscription": False,
        "recurring_cycle": None,
    }
    body.update(overrides)
    return body


class TestEditingAProduct:
    def test_an_admin_can_edit_a_product(self, client: TestClient) -> None:
        res = sign_in(client, ADMIN).put(
            PRODUCT, json=edit(name="Laptop Pro 14 (2026)", category="Devices")
        )

        assert res.status_code == 200
        data = res.json()["data"]
        assert data["name"] == "Laptop Pro 14 (2026)"
        assert data["category"] == "Devices"

    def test_the_change_persists_beyond_the_response(self, client: TestClient) -> None:
        """The PUT echoes the record back, so only a fresh GET proves it stuck."""
        admin = sign_in(client, ADMIN)
        admin.put(PRODUCT, json=edit(description="Now with a bigger battery."))

        data = admin.get(PRODUCT).json()["data"]
        assert data["description"] == "Now with a bigger battery."

    def test_a_new_price_is_reflected_in_the_detail_view(
        self, client: TestClient
    ) -> None:
        admin = sign_in(client, ADMIN)
        admin.put(PRODUCT, json=edit(unit_price=1350.50, cost_price=800))

        data = admin.get(PRODUCT).json()["data"]
        assert data["price"] == 1350.50
        assert data["cost_price"] == 800

    def test_the_price_change_reaches_the_catalogue_listing(
        self, client: TestClient
    ) -> None:
        admin = sign_in(client, ADMIN)
        admin.put(PRODUCT, json=edit(unit_price=1350.50))

        rows = {r["id"]: r for r in admin.get("/products").json()["data"]}
        assert rows["p1"]["price"] == 1350.50

    def test_a_subscription_keeps_its_cadence(self, client: TestClient) -> None:
        data = (
            sign_in(client, ADMIN)
            .put(
                PRODUCT,
                json=edit(is_subscription=True, recurring_cycle="Quarterly"),
            )
            .json()["data"]
        )
        assert data["subscription"] is True
        assert data["cadence"] == "Quarterly"

    def test_an_unknown_product_cannot_be_edited(self, client: TestClient) -> None:
        assert (
            sign_in(client, ADMIN).put("/products/p9999", json=edit()).status_code
            == 404
        )


class TestPermissions:
    def test_a_rep_may_read_the_catalogue_but_not_change_it(
        self, client: TestClient
    ) -> None:
        rep = sign_in(client, REP)
        assert rep.get(PRODUCT).status_code == 200
        assert rep.put(PRODUCT, json=edit(name="Renamed by a rep")).status_code == 403

    def test_a_rejected_edit_leaves_the_product_alone(self, client: TestClient) -> None:
        rep = sign_in(client, REP)
        rep.put(PRODUCT, json=edit(name="Renamed by a rep"))

        assert rep.get(PRODUCT).json()["data"]["name"] == "Laptop Pro 14"

    def test_a_customer_may_not_touch_the_catalogue(self, client: TestClient) -> None:
        client.post(
            "/auth/login",
            json={"email": "customer@acmecorp.com", "password": "dealflow123"},
        )
        assert client.put(PRODUCT, json=edit()).status_code == 403


class TestMarginIsProtected:
    def test_a_cost_above_the_price_is_rejected(self, client: TestClient) -> None:
        """A negative margin would silently poison deal health and reports."""
        res = sign_in(client, ADMIN).put(
            PRODUCT, json=edit(unit_price=100, cost_price=250)
        )

        assert res.status_code == 422
        assert "cost price" in res.json()["detail"]["message"].lower()

    def test_a_rejected_cost_is_not_written(self, client: TestClient) -> None:
        admin = sign_in(client, ADMIN)
        admin.put(PRODUCT, json=edit(unit_price=100, cost_price=250))

        data = admin.get(PRODUCT).json()["data"]
        assert data["price"] == 1200
        assert data["cost_price"] == 780

    def test_a_cost_equal_to_the_price_is_allowed(self, client: TestClient) -> None:
        """Zero margin is a real, if unhappy, business case - only negative is not."""
        res = sign_in(client, ADMIN).put(
            PRODUCT, json=edit(unit_price=900, cost_price=900)
        )
        assert res.status_code == 200
