"""Billing over HTTP: hybrid orders, proration, invoices, payments.

test_billing_proration.py proves the arithmetic. This proves the separation of
one-time from recurring, the credit-note path, and payment status.
"""

from fastapi.testclient import TestClient

FINANCE = {"email": "finance@dealflow360.com", "password": "dealflow123"}
REP = {"email": "rep@dealflow360.com", "password": "dealflow123"}


def sign_in(client: TestClient, who: dict) -> TestClient:
    client.post("/auth/login", json=who)
    return client


class TestHybridOrder:
    def test_one_time_and_recurring_are_reported_separately(
        self, client: TestClient
    ) -> None:
        """PS section 9 step 6."""
        data = (
            sign_in(client, FINANCE)
            .get("/subscriptions/s1/billing-detail")
            .json()["data"]
        )

        assert data["one_time_lines"]
        assert data["recurring_lines"]

    def test_a_one_time_product_never_appears_as_recurring(
        self, client: TestClient
    ) -> None:
        data = (
            sign_in(client, FINANCE)
            .get("/subscriptions/s1/billing-detail")
            .json()["data"]
        )

        one_time = {ln["product"] for ln in data["one_time_lines"]}
        recurring = {ln["plan"] for ln in data["recurring_lines"]}
        assert not one_time & recurring

    def test_the_one_time_invoice_is_its_own_document(self, client: TestClient) -> None:
        """Putting both on one document bills the laptop twelve times."""
        rows = sign_in(client, FINANCE).get("/invoices").json()["data"]

        assert rows
        # No document may mix the two. Asserting every invoice is ONE_TIME only
        # held while the seed contained nothing recurring.
        for row in rows:
            assert row["line_type"] in ("ONE_TIME", "RECURRING")

        hybrid = [r for r in rows if r["line_type"] == "ONE_TIME"]
        assert hybrid, "the hybrid order must produce a one-time document"
        for row in hybrid:
            detail = sign_in(client, FINANCE).get(f"/invoices/{row['id']}").json()
            lines = detail["data"]["lines"]
            assert not any(line.get("is_recurring") for line in lines)


class TestModify:
    def test_an_upgrade_charges_only_the_remaining_days(
        self, client: TestClient
    ) -> None:
        data = (
            sign_in(client, FINANCE)
            .post("/subscriptions/s1/modify", json={"qty": 3})
            .json()["data"]
        )

        assert data["is_credit"] is False
        assert 0 < data["amount"] < data["price_delta"]

    def test_the_change_appears_on_the_schedule_flagged_as_prorated(
        self, client: TestClient
    ) -> None:
        fin = sign_in(client, FINANCE)
        fin.post("/subscriptions/s1/modify", json={"qty": 3})

        schedule = fin.get("/subscriptions/s1/billing-detail").json()["data"][
            "schedule"
        ]
        assert any(row["is_prorated"] for row in schedule)

    def test_a_downgrade_raises_a_credit_note(self, client: TestClient) -> None:
        fin = sign_in(client, FINANCE)
        fin.post("/subscriptions/s1/modify", json={"qty": 3})
        before = len(fin.get("/invoices").json()["data"])

        result = fin.post("/subscriptions/s1/modify", json={"qty": 1}).json()["data"]

        assert result["is_credit"] is True
        assert len(fin.get("/invoices").json()["data"]) == before + 1

    def test_the_explanation_shows_the_working(self, client: TestClient) -> None:
        data = (
            sign_in(client, FINANCE)
            .post("/subscriptions/s1/modify", json={"qty": 2})
            .json()["data"]
        )

        assert "days remain" in data["explanation"]


class TestCancel:
    def test_cancelling_credits_the_unused_remainder(self, client: TestClient) -> None:
        data = sign_in(client, FINANCE).post("/subscriptions/s1/cancel").json()["data"]

        assert data["status"] == "Cancelled"
        assert data["credit_amount"] < 0
        assert data["credit_note"].startswith("CN-")

    def test_cancelling_twice_is_refused(self, client: TestClient) -> None:
        """Otherwise the customer is credited for the same days again."""
        fin = sign_in(client, FINANCE)
        fin.post("/subscriptions/s1/cancel")

        assert fin.post("/subscriptions/s1/cancel").status_code == 409

    def test_a_cancelled_subscription_cannot_be_modified(
        self, client: TestClient
    ) -> None:
        fin = sign_in(client, FINANCE)
        fin.post("/subscriptions/s1/cancel")

        assert fin.post("/subscriptions/s1/modify", json={"qty": 5}).status_code == 409


class TestPayments:
    def test_a_part_payment_reads_as_partial(self, client: TestClient) -> None:
        data = (
            sign_in(client, FINANCE)
            .post("/invoices/i1/record-payment", json={"amount": 100})
            .json()["data"]
        )

        assert data["status"] == "Partial"
        assert data["paid_amount"] == 100

    def test_payments_accumulate_rather_than_overwrite(
        self, client: TestClient
    ) -> None:
        """Two part-payments must reach PAID, not replace one another."""
        fin = sign_in(client, FINANCE)
        total = fin.get("/invoices/i1").json()["data"]["amount"]

        fin.post("/invoices/i1/record-payment", json={"amount": total / 2})
        data = fin.post(
            "/invoices/i1/record-payment", json={"amount": total / 2}
        ).json()["data"]

        assert data["status"] == "Paid"

    def test_paying_the_full_amount_reads_as_paid(self, client: TestClient) -> None:
        fin = sign_in(client, FINANCE)
        total = fin.get("/invoices/i1").json()["data"]["amount"]

        data = fin.post("/invoices/i1/record-payment", json={"amount": total}).json()[
            "data"
        ]

        assert data["status"] == "Paid"
        assert data["stage"] == "Paid"

    def test_an_already_paid_invoice_refuses_another_payment(
        self, client: TestClient
    ) -> None:
        fin = sign_in(client, FINANCE)
        total = fin.get("/invoices/i1").json()["data"]["amount"]
        fin.post("/invoices/i1/record-payment", json={"amount": total})

        assert (
            fin.post("/invoices/i1/record-payment", json={"amount": 10}).status_code
            == 409
        )

    def test_a_credit_note_cannot_take_a_payment(self, client: TestClient) -> None:
        """It is money owed to the customer, not by them."""
        fin = sign_in(client, FINANCE)
        fin.post("/subscriptions/s1/cancel")
        credit = next(
            row
            for row in fin.get("/invoices").json()["data"]
            if row["invoice_no"].startswith("CN-")
        )

        res = fin.post(f"/invoices/{credit['id']}/record-payment", json={"amount": 10})

        assert res.status_code == 409

    def test_an_unknown_invoice_is_not_found(self, client: TestClient) -> None:
        sign_in(client, FINANCE)
        assert client.get("/invoices/i9999").status_code == 404

    def test_a_customer_cannot_record_payments(self, client: TestClient) -> None:
        client.post(
            "/auth/login",
            json={"email": "customer@acmecorp.com", "password": "dealflow123"},
        )
        assert (
            client.post("/invoices/i1/record-payment", json={"amount": 10}).status_code
            == 403
        )


class TestWhoSettles:
    def test_a_rep_cannot_record_a_payment(self, client: TestClient) -> None:
        """PS section 3 puts reconciliation with Finance. Letting the rep who
        sold the deal also mark it paid removes the separation that makes the
        audit trail worth keeping."""
        res = sign_in(client, REP).post(
            "/invoices/i1/record-payment", json={"amount": 10}
        )

        assert res.status_code == 403

    def test_finance_can_and_the_invoice_records_who(self, client: TestClient) -> None:
        fin = sign_in(client, FINANCE)
        before = fin.get("/invoices/i1").json()["data"]

        fin.post("/invoices/i1/record-payment", json={"amount": 100})
        after = fin.get("/invoices/i1").json()["data"]

        assert after["recorded_by"] == "Riya Iyer"
        assert after["paid_at"]
        assert after["balance_due"] == round(before["amount"] - 100, 2)
        assert after["status"] == "Partial"

    def test_the_balance_never_goes_negative(self, client: TestClient) -> None:
        """An overpayment settles the invoice; it is not owed back on this line."""
        fin = sign_in(client, FINANCE)
        amount = fin.get("/invoices/i1").json()["data"]["amount"]

        fin.post("/invoices/i1/record-payment", json={"amount": amount + 500})
        after = fin.get("/invoices/i1").json()["data"]

        assert after["balance_due"] == 0
        assert after["status"] == "Paid"
