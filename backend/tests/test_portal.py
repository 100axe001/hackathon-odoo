"""The customer portal and the re-approval path.

PS section 9 step 7 is the scenario these cover: a customer talks the discount
past a threshold, confirms, and the quotation must go back for review rather
than confirming.
"""

from fastapi.testclient import TestClient

REP = {"email": "rep@dealflow360.com", "password": "dealflow123"}
MANAGER = {"email": "manager@dealflow360.com", "password": "dealflow123"}
CUSTOMER = {"email": "customer@acmecorp.com", "password": "dealflow123"}
FINANCE = {"email": "finance@dealflow360.com", "password": "dealflow123"}


def sign_in(client: TestClient, who: dict) -> TestClient:
    client.post("/auth/login", json=who)
    return client


def make_compliant_and_submit(client: TestClient) -> None:
    """Bring Q-1042 within its limits so it starts from an approved state."""
    rep = sign_in(client, REP)
    lines = rep.get("/quotations/q1").json()["data"]["lines"]
    service = next(ln for ln in lines if "Setup" in ln["product"])
    rep.patch(f"/quotations/q1/lines/{service['id']}", json={"discount_pct": 9})
    rep.post("/quotations/q1/submit")


class TestSeparation:
    """PS section 7: a real, separate, restricted view."""

    def test_a_customer_cannot_reach_internal_routes(self, client: TestClient) -> None:
        sign_in(client, CUSTOMER)

        assert client.get("/quotations").status_code == 403
        assert client.get("/approvals").status_code == 403
        assert client.get("/quotations/q1").status_code == 403

    def test_an_internal_user_cannot_reach_the_portal(self, client: TestClient) -> None:
        """The boundary holds in both directions, not just one."""
        sign_in(client, REP)
        assert client.get("/portal/quotations/q1").status_code == 403

    def test_the_portal_requires_a_session(self, client: TestClient) -> None:
        assert client.get("/portal/quotations/q1").status_code == 401


class TestPortalRead:
    def test_a_customer_sees_their_own_quotation(self, client: TestClient) -> None:
        sign_in(client, CUSTOMER)

        data = client.get("/portal/quotations/q1").json()["data"]

        assert data["number"] == "Q-1042"
        assert data["customer"] == "Acme Corp"
        assert len(data["lines"]) == 3

    def test_another_customers_quotation_is_not_found(self, client: TestClient) -> None:
        """Scoped, not filtered in the UI - changing the id must not work."""
        sign_in(client, CUSTOMER)
        assert client.get("/portal/quotations/q999").status_code == 404


class TestNegotiation:
    def test_a_counter_offer_puts_the_quote_under_negotiation(
        self, client: TestClient
    ) -> None:
        make_compliant_and_submit(client)
        sign_in(client, CUSTOMER)

        data = client.post(
            "/portal/quotations/q1/negotiate",
            json={"counter_discount_pct": 22, "note": "Ready to sign at 22%"},
        ).json()["data"]

        assert data["status"] == "Negotiation"

    def test_the_request_appears_in_the_thread(self, client: TestClient) -> None:
        make_compliant_and_submit(client)
        sign_in(client, CUSTOMER)
        client.post(
            "/portal/quotations/q1/negotiate",
            json={"counter_discount_pct": 22, "note": "Ready to sign at 22%"},
        )

        comments = client.get("/portal/quotations/q1").json()["data"]["comments"]

        assert len(comments) == 1
        assert comments[0]["counter_discount_pct"] == 22.0
        assert comments[0]["author"] == "Devon Cole"


class TestReapproval:
    def test_confirming_within_limits_confirms_the_order(
        self, client: TestClient
    ) -> None:
        make_compliant_and_submit(client)
        sign_in(client, CUSTOMER)

        data = client.post("/portal/quotations/q1/confirm").json()["data"]

        assert data["status"] == "Confirmed"
        assert data["reentered_approval"] is False

    def test_confirming_beyond_limits_re_enters_approval(
        self, client: TestClient
    ) -> None:
        """PS section 9 step 7. The whole point of the portal being governed."""
        make_compliant_and_submit(client)
        sign_in(client, CUSTOMER)
        client.post(
            "/portal/quotations/q1/negotiate", json={"counter_discount_pct": 22}
        )

        data = client.post("/portal/quotations/q1/confirm").json()["data"]

        assert data["reentered_approval"] is True
        assert data["status"] == "Pending Approval"
        assert data["risk_level"] == "HIGH"
        assert data["required_approval"] == ["SALES_MANAGER", "FINANCE"]

    def test_the_customer_is_told_why_in_plain_language(
        self, client: TestClient
    ) -> None:
        make_compliant_and_submit(client)
        sign_in(client, CUSTOMER)
        client.post(
            "/portal/quotations/q1/negotiate", json={"counter_discount_pct": 22}
        )

        explanation = client.post("/portal/quotations/q1/confirm").json()["data"][
            "explanation"
        ]

        assert "over its own limit" in explanation

    def test_it_lands_back_in_the_managers_queue(self, client: TestClient) -> None:
        make_compliant_and_submit(client)
        sign_in(client, CUSTOMER)
        client.post(
            "/portal/quotations/q1/negotiate", json={"counter_discount_pct": 22}
        )
        client.post("/portal/quotations/q1/confirm")

        queue = sign_in(client, MANAGER).get("/approvals").json()["data"]

        # It must be in the queue and waiting on the manager. Asserting the
        # queue held nothing else only worked while the seed was that small.
        row = next(r for r in queue if r["quotation"] == "Q-1042")
        assert row["stage"] == "SALES_MANAGER"

    def test_the_negotiation_is_on_the_audit_trail(self, client: TestClient) -> None:
        make_compliant_and_submit(client)
        sign_in(client, CUSTOMER)
        client.post(
            "/portal/quotations/q1/negotiate", json={"counter_discount_pct": 22}
        )
        client.post("/portal/quotations/q1/confirm")

        trail = (
            sign_in(client, MANAGER)
            .get("/quotations/q1/approval-detail")
            .json()["data"]["audit_trail"]
        )

        actions = [row["action"] for row in trail]
        assert "NEGOTIATE" in actions
        assert "CONFIRM" in actions
        assert any(row["user"] == "Devon Cole" for row in trail)


class TestAfterTheSale:
    """The brief's portal stops at the quotation. Once a customer confirms, the
    questions become "where is my order" and "what do I owe"."""

    def test_orders_show_where_each_part_ships_from(self, client: TestClient) -> None:
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

        orders = sign_in(client, CUSTOMER).get("/portal/orders").json()["data"]

        order = next(o for o in orders if o["number"] == "Q-1042")
        assert order["shipments"], "an accepted split must be visible to the customer"
        assert all(s["product"] for s in order["shipments"])
        assert order["fulfillment"] != "SPLIT_ACCEPTED", "internal enum leaked"

    def test_a_draft_is_never_shown_to_the_customer(self, client: TestClient) -> None:
        """A quotation the rep is still building is not the customer's business."""
        orders = sign_in(client, CUSTOMER).get("/portal/orders").json()["data"]

        assert all(o["status"] in ("Approved", "Confirmed") for o in orders)

    def test_billing_reports_what_is_still_owed(self, client: TestClient) -> None:
        data = sign_in(client, CUSTOMER).get("/portal/billing").json()["data"]

        assert data["invoices"], "the seeded hybrid order raises an invoice"
        for row in data["invoices"]:
            assert row["balance_due"] >= 0
        assert data["total_outstanding"] >= 0

    def test_the_profile_names_the_tier_that_sets_the_ceiling(
        self, client: TestClient
    ) -> None:
        data = sign_in(client, CUSTOMER).get("/portal/profile").json()["data"]

        assert data["company"] == "Acme Corp"
        assert data["tier"] == "Gold"
        assert data["contact_email"] == "customer@acmecorp.com"

    def test_an_internal_user_cannot_read_portal_data(self, client: TestClient) -> None:
        for path in ("/portal/orders", "/portal/billing", "/portal/profile"):
            assert sign_in(client, REP).get(path).status_code == 403


class TestWhatTheCustomerMayActOn:
    def test_confirming_twice_is_refused(self, client: TestClient) -> None:
        """The second click used to return success and change nothing, which is
        indistinguishable from a broken button."""
        cust = sign_in(client, CUSTOMER)
        confirmed = next(
            q
            for q in cust.get("/portal/quotations").json()["data"]
            if q["status"] == "Confirmed"
        )

        res = cust.post(f"/portal/quotations/{confirmed['id']}/confirm")

        assert res.status_code == 409
        assert "already confirmed" in res.json()["detail"]["message"]

    def test_confirming_mid_approval_cannot_erase_a_decision(
        self, client: TestClient
    ) -> None:
        """Confirming rebuilds the approval chain. Allowing it while reviewers
        are part-way through would silently discard a manager's sign-off."""
        sign_in(client, REP).post("/quotations/q1/submit")

        res = sign_in(client, CUSTOMER).post("/portal/quotations/q1/confirm")

        assert res.status_code == 409
        assert "with our team" in res.json()["detail"]["message"]

        detail = sign_in(client, MANAGER).get("/quotations/q1/approval-detail").json()
        assert detail["data"]["stage"] == "SALES_MANAGER"

    def test_negotiating_a_finished_quotation_is_refused(
        self, client: TestClient
    ) -> None:
        cust = sign_in(client, CUSTOMER)
        confirmed = next(
            q
            for q in cust.get("/portal/quotations").json()["data"]
            if q["status"] == "Confirmed"
        )

        res = cust.post(
            f"/portal/quotations/{confirmed['id']}/negotiate",
            json={"counter_discount_pct": 30},
        )

        assert res.status_code == 409

    def test_a_finished_quotation_is_still_readable(self, client: TestClient) -> None:
        """Gating the actions must not gate the record - a customer should be
        able to look back at a deal they agreed months ago."""
        cust = sign_in(client, CUSTOMER)
        confirmed = next(
            q
            for q in cust.get("/portal/quotations").json()["data"]
            if q["status"] == "Confirmed"
        )

        data = cust.get(f"/portal/quotations/{confirmed['id']}").json()["data"]

        assert data["lines"]
        assert data["can_act"] is False
        assert data["blocked_reason"]
