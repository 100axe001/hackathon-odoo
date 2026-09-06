"""Opening a quotation, and moving one across the pipeline board.

The board is the one place a status can be written without the risk engine
running, so most of this file is about what a drag is *not* allowed to do.
"""

from fastapi.testclient import TestClient

REP = {"email": "rep@dealflow360.com", "password": "dealflow123"}
REP2 = {"email": "rep2@dealflow360.com", "password": "dealflow123"}
MANAGER = {"email": "manager@dealflow360.com", "password": "dealflow123"}
CUSTOMER = {"email": "customer@acmecorp.com", "password": "dealflow123"}

ACME = 1


def sign_in(client: TestClient, who: dict) -> TestClient:
    client.post("/auth/login", json=who)
    return client


def number_of(response) -> str:
    """The created quotation's number, which the message leads with."""
    return response.json()["message"].split()[0]


class TestCreating:
    def test_a_new_quotation_starts_empty_and_ready_to_open(
        self, rep_client: TestClient
    ) -> None:
        res = rep_client.post("/quotations", json={"customer_id": ACME})

        assert res.status_code == 201
        data = res.json()["data"]
        assert data["customer_name"] == "Acme Corp"
        assert data["lines"] == []
        assert data["net_total"] == 0

    def test_the_response_is_the_shape_the_detail_screen_reads(
        self, rep_client: TestClient
    ) -> None:
        """The UI navigates straight into the new quotation, so create has to
        return what GET /quotations/{id} returns."""
        created = rep_client.post("/quotations", json={"customer_id": ACME}).json()[
            "data"
        ]

        fetched = rep_client.get(f"/quotations/{created['id']}").json()["data"]

        assert fetched.keys() == created.keys()
        assert fetched["id"] == created["id"]

    def test_the_caller_owns_what_they_create(self, client: TestClient) -> None:
        """rep_id comes from the session, so a quotation one rep opens must
        appear for them and for nobody else."""
        rep2 = sign_in(client, REP2)
        created = rep2.post("/quotations", json={"customer_id": ACME}).json()["data"]

        assert created["id"] in [
            row["id"] for row in rep2.get("/quotations").json()["data"]
        ]

        theirs = sign_in(client, REP).get("/quotations").json()["data"]
        assert all(row["id"] != created["id"] for row in theirs)

    def test_the_body_cannot_hand_ownership_to_another_rep(
        self, client: TestClient
    ) -> None:
        """Otherwise a rep could file a quote under a colleague and escape both
        the row scoping and their own discount-anomaly baseline."""
        rep2 = sign_in(client, REP2)
        created = rep2.post(
            "/quotations", json={"customer_id": ACME, "rep_id": 1}
        ).json()["data"]

        assert rep2.get(f"/quotations/{created['id']}").status_code == 200

        # Scoping hides another rep's quotation outright, so the 404 is the
        # proof that rep_id in the body was ignored.
        assert (
            sign_in(client, REP).get(f"/quotations/{created['id']}").status_code == 404
        )

    def test_the_generated_number_does_not_collide(
        self, rep_client: TestClient
    ) -> None:
        """seed.py already holds numbers in the Q-10xx range, so a scheme that
        counted rows instead of reading the maximum would reissue one and the
        unique constraint would reject it."""
        created = [
            rep_client.post("/quotations", json={"customer_id": ACME}) for _ in range(3)
        ]

        # A collision with anything seeded fails here, whatever the seed holds.
        assert all(res.status_code == 201 for res in created)
        numbers = [number_of(res) for res in created]
        assert all(n.startswith("Q-") for n in numbers)

        # Consecutive, which is "highest + 1" stated without naming the seed's
        # highest - that number moves every time seed.py grows.
        suffixes = [int(n.removeprefix("Q-")) for n in numbers]
        assert suffixes == [suffixes[0], suffixes[0] + 1, suffixes[0] + 2]

    def test_an_unknown_customer_is_a_404(self, rep_client: TestClient) -> None:
        assert (
            rep_client.post("/quotations", json={"customer_id": 9999}).status_code
            == 404
        )

    def test_a_customer_cannot_create_a_quotation(self, client: TestClient) -> None:
        """PS section 7: the portal is a restricted view, not a second desk."""
        sign_in(client, CUSTOMER)

        res = client.post("/quotations", json={"customer_id": ACME})

        assert res.status_code == 403

    def test_an_anonymous_caller_cannot(self, client: TestClient) -> None:
        assert client.post("/quotations", json={"customer_id": ACME}).status_code == 401


class TestPipelineDrag:
    """Dragging a card is allowed only for the moves no other endpoint owns."""

    def test_a_draft_can_be_dragged_into_negotiation(
        self, rep_client: TestClient
    ) -> None:
        res = rep_client.post("/quotations/q1/stage", json={"status": "Negotiation"})

        assert res.status_code == 200
        assert res.json()["data"]["status"] == "Negotiation"

    def test_the_move_survives_a_reload(self, rep_client: TestClient) -> None:
        """The whole point: before this, a refresh snapped the card back."""
        rep_client.post("/quotations/q1/stage", json={"status": "Negotiation"})

        rows = rep_client.get("/quotations").json()["data"]
        assert next(r for r in rows if r["id"] == "q1")["status"] == "Negotiation"

    def test_it_can_be_dragged_back_to_draft(self, rep_client: TestClient) -> None:
        rep_client.post("/quotations/q1/stage", json={"status": "Negotiation"})

        res = rep_client.post("/quotations/q1/stage", json={"status": "Draft"})

        assert res.status_code == 200
        assert res.json()["data"]["status"] == "Draft"

    def test_dropping_a_card_on_its_own_column_changes_nothing(
        self, rep_client: TestClient
    ) -> None:
        res = rep_client.post("/quotations/q1/stage", json={"status": "Draft"})

        assert res.status_code == 200
        assert res.json()["data"]["status"] == "Draft"

    def test_an_unknown_stage_is_refused(self, rep_client: TestClient) -> None:
        res = rep_client.post("/quotations/q1/stage", json={"status": "Shipped"})

        assert res.status_code == 400

    def test_a_customer_cannot_drag(self, client: TestClient) -> None:
        sign_in(client, CUSTOMER)

        res = client.post("/quotations/q1/stage", json={"status": "Negotiation"})

        assert res.status_code == 403


class TestDragCannotBypassGovernance:
    """The reason the permitted set is two moves and not six."""

    def test_a_drag_cannot_approve_a_quotation(self, rep_client: TestClient) -> None:
        res = rep_client.post("/quotations/q1/stage", json={"status": "Approved"})

        assert res.status_code == 400
        assert "/submit" in res.json()["detail"]["message"]

    def test_a_drag_cannot_send_a_quote_into_approval(
        self, rep_client: TestClient
    ) -> None:
        res = rep_client.post(
            "/quotations/q1/stage", json={"status": "Pending Approval"}
        )

        assert res.status_code == 400
        assert "/submit" in res.json()["detail"]["message"]

    def test_a_drag_cannot_confirm_an_order(self, rep_client: TestClient) -> None:
        res = rep_client.post("/quotations/q1/stage", json={"status": "Confirmed"})

        assert res.status_code == 400
        assert "/portal/quotations/{id}/confirm" in res.json()["detail"]["message"]

    def test_a_drag_cannot_reject_a_quotation(self, rep_client: TestClient) -> None:
        res = rep_client.post("/quotations/q1/stage", json={"status": "Rejected"})

        assert res.status_code == 400
        assert "/approve" in res.json()["detail"]["message"]

    def test_a_drag_cannot_pull_a_quote_out_of_a_live_approval_chain(
        self, rep_client: TestClient
    ) -> None:
        """q1 is 8pt over on the service line, so submitting routes it HIGH."""
        assert (
            rep_client.post("/quotations/q1/submit").json()["data"]["status"]
            == "Pending Approval"
        )

        res = rep_client.post("/quotations/q1/stage", json={"status": "Draft"})

        assert res.status_code == 400
        assert "/approve" in res.json()["detail"]["message"]

    def test_the_approval_chain_is_untouched_by_a_refused_drag(
        self, client: TestClient
    ) -> None:
        rep = sign_in(client, REP)
        rep.post("/quotations/q1/submit")
        rep.post("/quotations/q1/stage", json={"status": "Approved"})

        detail = (
            sign_in(client, MANAGER)
            .get("/quotations/q1/approval-detail")
            .json()["data"]
        )

        assert detail["stage"] == "SALES_MANAGER"
        assert [step["status"] for step in detail["steps"]] == ["PENDING", "PENDING"]
