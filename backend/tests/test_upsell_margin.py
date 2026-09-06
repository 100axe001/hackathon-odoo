"""Upsell suggestions and the live margin indicator.

PS section 9 step 4: accept one suggestion and confirm the order total and the
margin update right away.
"""

from fastapi.testclient import TestClient

REP = {"email": "rep@dealflow360.com", "password": "dealflow123"}


def sign_in(client: TestClient, who: dict) -> TestClient:
    client.post("/auth/login", json=who)
    return client


class TestMargin:
    def test_the_builder_reports_margin(self, rep_client: TestClient) -> None:
        data = rep_client.get("/quotations/q1").json()["data"]

        assert data["margin"] > 0
        assert 0 < data["margin_pct"] < 100

    def test_a_deeper_discount_eats_margin(self, rep_client: TestClient) -> None:
        """Cost does not move with the discount - that is why ceilings exist."""
        before = rep_client.get("/quotations/q1").json()["data"]["margin"]

        lines = rep_client.get("/quotations/q1").json()["data"]["lines"]
        laptop = next(ln for ln in lines if "Laptop" in ln["product"])
        rep_client.patch(
            f"/quotations/q1/lines/{laptop['id']}", json={"discount_pct": 14}
        )

        after = rep_client.get("/quotations/q1").json()["data"]["margin"]
        assert after < before


class TestSuggestions:
    def test_suggestions_are_returned_for_what_is_on_the_quote(
        self, rep_client: TestClient
    ) -> None:
        data = rep_client.get("/quotations/q1/upsell-suggestions").json()["data"]
        assert data

    def test_each_suggestion_carries_a_real_margin_delta(
        self, rep_client: TestClient
    ) -> None:
        """Computed from cost_price, which earlier drafts of the model lacked."""
        data = rep_client.get("/quotations/q1/upsell-suggestions").json()["data"]
        assert all(row["margin_delta"] > 0 for row in data)

    def test_a_promoted_product_carries_its_tag(self, rep_client: TestClient) -> None:
        data = rep_client.get("/quotations/q1/upsell-suggestions").json()["data"]
        assert any(row["promo_tag"] for row in data)

    def test_nothing_already_on_the_quotation_is_suggested(
        self, rep_client: TestClient
    ) -> None:
        detail = rep_client.get("/quotations/q1").json()["data"]
        on_quote = {ln["product"] for ln in detail["lines"]}

        suggestions = rep_client.get("/quotations/q1/upsell-suggestions").json()["data"]

        assert not on_quote & {row["product"] for row in suggestions}


class TestAcceptingASuggestion:
    def test_the_total_and_margin_update_immediately(
        self, rep_client: TestClient
    ) -> None:
        """PS section 9 step 4."""
        before = rep_client.get("/quotations/q1").json()["data"]
        suggestion = rep_client.get("/quotations/q1/upsell-suggestions").json()["data"][
            0
        ]

        after = rep_client.post(
            "/quotations/q1/lines",
            json={"product_id": suggestion["product_id"], "qty": 2},
        ).json()["data"]

        assert len(after["lines"]) == len(before["lines"]) + 1
        assert after["net_total"] > before["net_total"]
        assert after["margin"] > before["margin"]

    def test_the_added_line_starts_within_its_limit(
        self, rep_client: TestClient
    ) -> None:
        suggestion = rep_client.get("/quotations/q1/upsell-suggestions").json()["data"][
            0
        ]

        data = rep_client.post(
            "/quotations/q1/lines", json={"product_id": suggestion["product_id"]}
        ).json()["data"]

        added = data["lines"][-1]
        assert added["discount_pct"] == 0
        assert added["status"] == "OK"

    def test_adding_is_recorded_on_the_audit_trail(self, client: TestClient) -> None:
        rep = sign_in(client, REP)
        suggestion = rep.get("/quotations/q1/upsell-suggestions").json()["data"][0]
        rep.post("/quotations/q1/lines", json={"product_id": suggestion["product_id"]})

        trail = (
            sign_in(
                client, {"email": "manager@dealflow360.com", "password": "dealflow123"}
            )
            .get("/quotations/q1/approval-detail")
            .json()["data"]["audit_trail"]
        )

        assert any("Added" in (row["note"] or "") for row in trail)

    def test_an_unknown_product_is_not_found(self, rep_client: TestClient) -> None:
        res = rep_client.post("/quotations/q1/lines", json={"product_id": 9999})
        assert res.status_code == 404
