"""The deal journey, and the role capabilities PS section 3 assigns.

The journey exists so the workspace reads as one flow rather than five tabs
that each know only their own step; these tests pin that it advances with the
deal rather than describing a state it has left behind.
"""

from fastapi.testclient import TestClient

REP = {"email": "rep@dealflow360.com", "password": "dealflow123"}
MANAGER = {"email": "manager@dealflow360.com", "password": "dealflow123"}
FINANCE = {"email": "finance@dealflow360.com", "password": "dealflow123"}
ADMIN = {"email": "admin@dealflow360.com", "password": "dealflow123"}
CUSTOMER = {"email": "customer@acmecorp.com", "password": "dealflow123"}


def sign_in(client: TestClient, who: dict) -> TestClient:
    client.post("/auth/login", json=who)
    return client


def stages(client: TestClient) -> dict:
    data = client.get("/quotations/q1/journey").json()["data"]
    return {s["key"]: s["state"] for s in data["stages"]}


def next_action(client: TestClient) -> dict | None:
    return client.get("/quotations/q1/journey").json()["data"]["next_action"]


class TestJourney:
    def test_it_advances_with_the_deal(self, client: TestClient) -> None:
        rep = sign_in(client, REP)
        assert stages(rep)["build"] == "current"
        assert next_action(rep)["label"] == "Submit for approval"

        rep.post("/quotations/q1/submit")
        assert stages(rep)["approval"] == "current"
        assert next_action(rep)["role"] == "Sales Manager"

        sign_in(client, MANAGER).post(
            "/quotations/q1/approve", json={"decision": "approve"}
        )
        assert next_action(client)["role"] == "Finance"

        sign_in(client, FINANCE).post(
            "/quotations/q1/approve", json={"decision": "approve"}
        )
        after = stages(client)
        assert after["approval"] == "done"
        assert after["fulfillment"] == "current"

        rep = sign_in(client, REP)
        rep.get("/quotations/q1/fulfillment-split")
        rep.post("/quotations/q1/fulfillment/accept")
        assert stages(rep)["fulfillment"] == "done"

    def test_it_names_one_next_step_not_a_menu(self, client: TestClient) -> None:
        """Offering three choices puts the guesswork straight back."""
        action = next_action(sign_in(client, REP))

        assert action is not None
        assert set(action) == {"label", "path", "role"}


class TestRolesTheBriefAssigns:
    def test_a_rep_can_answer_a_customer(self, client: TestClient) -> None:
        """PS section 3: a rep responds to customer negotiation requests. There
        was no endpoint for it at all - the counter arrived as a number with
        nowhere to reply."""
        sign_in(client, REP).post("/quotations/q1/submit")
        sign_in(client, MANAGER).post(
            "/quotations/q1/approve", json={"decision": "approve"}
        )
        sign_in(client, FINANCE).post(
            "/quotations/q1/approve", json={"decision": "approve"}
        )
        sign_in(client, CUSTOMER).post(
            "/portal/quotations/q1/negotiate",
            json={"counter_discount_pct": 22, "note": "Can you move on this?"},
        )

        res = sign_in(client, REP).post(
            "/quotations/q1/messages", json={"body": "We can go to 12%."}
        )

        assert res.status_code == 201
        thread = res.json()["data"]
        assert [m["role"] for m in thread] == ["Customer", "Us"]

        # and it reaches the customer's own side of the conversation
        portal = sign_in(client, CUSTOMER).get("/portal/quotations/q1").json()["data"]
        assert any("12%" in (c["body"] or "") for c in portal["comments"])

    def test_a_manager_configures_tiers_and_the_chain(self, client: TestClient) -> None:
        """PS section 3 gives this to the Sales Manager, not only the admin."""
        manager = sign_in(client, MANAGER)
        current = manager.get("/admin/discount-config").json()["data"]

        saved = manager.put(
            "/admin/discount-config",
            json={
                "tier_ceilings": current["tier_ceilings"],
                "category_ceilings": current["category_ceilings"],
            },
        )
        chain = manager.put(
            "/admin/approval-rules",
            json={
                "rules": [
                    {"level": "MEDIUM", "step_order": 1, "role": "SALES_MANAGER"},
                    {"level": "HIGH", "step_order": 1, "role": "SALES_MANAGER"},
                ]
            },
        )

        assert saved.status_code == 200
        assert chain.status_code == 200

    def test_a_manager_still_cannot_touch_backend_setup(
        self, client: TestClient
    ) -> None:
        """Products, warehouses and plans stay with the admin, which is where
        the same section puts them."""
        manager = sign_in(client, MANAGER)
        warehouses = manager.get("/admin/warehouses").json()["data"]

        assert (
            manager.put(
                "/admin/warehouses", json={"warehouses": warehouses}
            ).status_code
            == 403
        )

    def test_a_rep_cannot_configure_ceilings(self, client: TestClient) -> None:
        rep = sign_in(client, REP)
        current = rep.get("/admin/discount-config").json()["data"]

        res = rep.put(
            "/admin/discount-config",
            json={
                "tier_ceilings": current["tier_ceilings"],
                "category_ceilings": current["category_ceilings"],
            },
        )

        assert res.status_code == 403
