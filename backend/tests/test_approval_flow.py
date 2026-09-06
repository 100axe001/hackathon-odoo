"""The graded core, end to end over HTTP.

test_blended.py proves the arithmetic. This proves the routing, the governance
rules, and the audit trail actually hold through the API.
"""

from fastapi.testclient import TestClient

REP = {"email": "rep@dealflow360.com", "password": "dealflow123"}
REP2 = {"email": "rep2@dealflow360.com", "password": "dealflow123"}
MANAGER = {"email": "manager@dealflow360.com", "password": "dealflow123"}
FINANCE = {"email": "finance@dealflow360.com", "password": "dealflow123"}


def _status(client: TestClient, quotation_id: str = "q1") -> str:
    """Stage lives on the list row; the detail response carries pricing only."""
    rows = client.get("/quotations").json()["data"]
    return next(r["status"] for r in rows if r["id"] == quotation_id)


def sign_in(client: TestClient, who: dict) -> TestClient:
    client.post("/auth/login", json=who)
    return client


class TestLineValidation:
    def test_the_ceiling_is_the_stricter_of_tier_and_category(
        self, rep_client: TestClient
    ) -> None:
        """Acme is Gold (15%), but Services caps at 10% - so the line gets 10."""
        lines = rep_client.get("/quotations/q1").json()["data"]["lines"]
        service = next(ln for ln in lines if "Setup" in ln["product"])

        assert service["limit_pct"] == 10.0
        assert service["status"] == "OVER"

    def test_a_hardware_line_gets_the_looser_ceiling(
        self, rep_client: TestClient
    ) -> None:
        lines = rep_client.get("/quotations/q1").json()["data"]["lines"]
        laptop = next(ln for ln in lines if "Laptop" in ln["product"])

        assert laptop["limit_pct"] == 15.0
        assert laptop["status"] == "OK"

    def test_editing_a_discount_revalidates_against_that_line_ceiling(
        self, rep_client: TestClient
    ) -> None:
        lines = rep_client.get("/quotations/q1").json()["data"]["lines"]
        service = next(ln for ln in lines if "Setup" in ln["product"])

        res = rep_client.patch(
            f"/quotations/q1/lines/{service['id']}", json={"discount_pct": 9}
        )

        data = res.json()["data"]
        assert data["status"] == "OK"
        assert data["over_by_pct"] == 0.0

    def test_the_frontend_cannot_decide_the_limit(self, rep_client: TestClient) -> None:
        """The response carries the ceiling, so the client only renders it."""
        lines = rep_client.get("/quotations/q1").json()["data"]["lines"]
        service = next(ln for ln in lines if "Setup" in ln["product"])

        data = rep_client.patch(
            f"/quotations/q1/lines/{service['id']}", json={"discount_pct": 40}
        ).json()["data"]

        assert data["allowed_discount_pct"] == 10.0
        assert data["over_by_pct"] == 30.0


class TestRouting:
    def test_an_over_limit_quote_routes_itself_without_being_asked(
        self, rep_client: TestClient
    ) -> None:
        """PS section 9 step 3: the rep never requests approval manually."""
        data = rep_client.post("/quotations/q1/submit").json()["data"]

        assert data["risk_level"] == "HIGH"
        assert data["decided_by"] == "WORST_LINE"
        assert data["required_approval"] == ["SALES_MANAGER", "FINANCE"]
        assert data["status"] == "Pending Approval"

    def test_a_compliant_quote_is_auto_approved(self, rep_client: TestClient) -> None:
        lines = rep_client.get("/quotations/q1").json()["data"]["lines"]
        service = next(ln for ln in lines if "Setup" in ln["product"])
        rep_client.patch(
            f"/quotations/q1/lines/{service['id']}", json={"discount_pct": 5}
        )

        data = rep_client.post("/quotations/q1/submit").json()["data"]

        assert data["risk_level"] == "LOW"
        assert data["required_approval"] == []
        assert data["status"] == "Approved"

    def test_the_explanation_names_the_line_that_caused_it(
        self, rep_client: TestClient
    ) -> None:
        """PS section 5 forbids hardcoding this text."""
        data = rep_client.post("/quotations/q1/submit").json()["data"]
        assert "Onsite Setup Service" in data["explanation"]
        assert "8.00pt" in data["explanation"]


class TestListing:
    def test_the_list_shows_a_real_amount(self, rep_client: TestClient) -> None:
        """total_net_value is only written when a quotation is scored, so the
        list has to compute from the lines or every row reads as $0."""
        rows = rep_client.get("/quotations").json()["data"]
        assert all(row["amount"] > 0 for row in rows)


class TestGovernance:
    def test_a_rep_cannot_approve_their_own_quotation(
        self, rep_client: TestClient
    ) -> None:
        """The premise of the whole product."""
        rep_client.post("/quotations/q1/submit")

        res = rep_client.post("/quotations/q1/approve", json={"decision": "approve"})

        assert res.status_code == 403
        assert "your own" in res.json()["detail"]["message"]

    def test_a_returned_quotation_cannot_still_be_approved(
        self, client: TestClient
    ) -> None:
        """Returning sets the quotation back to Draft but leaves the later steps
        PENDING. Without a status check the finance step is still actionable, so
        an approver could drive a Draft straight to Approved and skip the rep's
        revision entirely - the routing would be real but trivially sidestepped."""
        sign_in(client, REP).post("/quotations/q1/submit")
        sign_in(client, MANAGER).post(
            "/quotations/q1/approve", json={"decision": "return"}
        )
        assert _status(sign_in(client, REP)) == "Draft"

        res = sign_in(client, FINANCE).post(
            "/quotations/q1/approve", json={"decision": "approve"}
        )

        assert res.status_code == 409
        assert "submitted again" in res.json()["detail"]["message"]
        assert _status(sign_in(client, REP)) == "Draft"

    def test_finance_cannot_act_before_the_manager(self, client: TestClient) -> None:
        sign_in(client, REP).post("/quotations/q1/submit")

        res = sign_in(client, FINANCE).post(
            "/quotations/q1/approve", json={"decision": "approve"}
        )

        assert res.status_code == 403
        assert "SALES_MANAGER" in res.json()["detail"]["message"]

    def test_a_customer_is_rejected_by_every_internal_route(
        self, client: TestClient
    ) -> None:
        """PS section 7: the portal is a restricted view, not a relabelled one."""
        client.post(
            "/auth/login",
            json={"email": "customer@acmecorp.com", "password": "dealflow123"},
        )

        assert client.get("/quotations").status_code == 403
        assert client.get("/approvals").status_code == 403

    def test_a_rep_sees_only_their_own_quotations(self, client: TestClient) -> None:
        """Asserts the scoping property, not a row count.

        A count broke as soon as the seed grew, while telling us nothing about
        whether scoping actually worked.
        """
        mine = sign_in(client, REP).get("/quotations").json()["data"]
        theirs = sign_in(client, REP2).get("/quotations").json()["data"]

        assert mine, "the seeded rep should own at least one quotation"
        assert theirs, "rep2 should own at least one quotation too"

        # Disjointness is the property. Asserting one rep sees an empty list
        # only held while the seed happened to give them nothing.
        assert not {row["id"] for row in mine} & {row["id"] for row in theirs}

        everyone = sign_in(client, MANAGER).get("/quotations").json()["data"]
        assert len(everyone) > len(mine), "a manager is not scoped to one rep"


class TestChainAndAudit:
    def test_both_reviewers_must_act_before_it_is_approved(
        self, client: TestClient
    ) -> None:
        sign_in(client, REP).post("/quotations/q1/submit")

        after_manager = (
            sign_in(client, MANAGER)
            .post("/quotations/q1/approve", json={"decision": "approve"})
            .json()["data"]
        )
        assert after_manager["status"] == "Pending Approval"
        assert after_manager["stage"] == "FINANCE"

        after_finance = (
            sign_in(client, FINANCE)
            .post("/quotations/q1/approve", json={"decision": "approve"})
            .json()["data"]
        )
        assert after_finance["status"] == "Approved"
        assert after_finance["complete"] is True

    def test_returning_sends_it_back_to_draft(self, client: TestClient) -> None:
        sign_in(client, REP).post("/quotations/q1/submit")

        data = (
            sign_in(client, MANAGER)
            .post(
                "/quotations/q1/approve",
                json={"decision": "return", "comment": "Justify the service discount"},
            )
            .json()["data"]
        )

        assert data["status"] == "Draft"

    def test_every_action_lands_in_the_audit_trail_with_a_user(
        self, client: TestClient
    ) -> None:
        """PS section 4 A3: user, timestamp and reason on every action."""
        sign_in(client, REP).post("/quotations/q1/submit")
        sign_in(client, MANAGER).post(
            "/quotations/q1/approve",
            json={"decision": "approve", "comment": "Approved on volume"},
        )

        trail = (
            sign_in(client, MANAGER)
            .get("/quotations/q1/approval-detail")
            .json()["data"]["audit_trail"]
        )

        actions = [row["action"] for row in trail]
        assert "SUBMIT" in actions
        assert "APPROVE" in actions
        assert all(row["user"] for row in trail)
        assert any(row["note"] == "Approved on volume" for row in trail)

    def test_a_lower_risk_resubmission_needs_fewer_reviewers(
        self, client: TestClient
    ) -> None:
        """The chain is rebuilt from the new score, not carried over."""
        rep = sign_in(client, REP)
        rep.post("/quotations/q1/submit")
        sign_in(client, MANAGER).post(
            "/quotations/q1/approve", json={"decision": "return"}
        )

        rep = sign_in(client, REP)
        lines = rep.get("/quotations/q1").json()["data"]["lines"]
        service = next(ln for ln in lines if "Setup" in ln["product"])
        rep.patch(f"/quotations/q1/lines/{service['id']}", json={"discount_pct": 12})

        data = rep.post("/quotations/q1/submit").json()["data"]

        assert data["risk_level"] == "MEDIUM"
        assert data["required_approval"] == ["SALES_MANAGER"]
