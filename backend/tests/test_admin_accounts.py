"""Account administration.

Self-signup cannot create a privileged role or a portal account, so an admin
path has to exist - otherwise no customer could ever reach the portal.
"""

from fastapi.testclient import TestClient

ADMIN = {"email": "admin@dealflow360.com", "password": "dealflow123"}
REP = {"email": "rep@dealflow360.com", "password": "dealflow123"}


def sign_in(client: TestClient, who: dict) -> TestClient:
    client.post("/auth/login", json=who)
    return client


NEW_CUSTOMER = {
    "email": "buyer@betaindustries.com",
    "password": "password123",
    "full_name": "Priya Menon",
    "role": "CUSTOMER",
    "customer_id": 2,
}


class TestWhoMayCreateAccounts:
    def test_a_rep_cannot_create_accounts(self, client: TestClient) -> None:
        sign_in(client, REP)
        res = client.post("/admin/users", json=NEW_CUSTOMER)
        assert res.status_code == 403

    def test_an_anonymous_caller_cannot(self, client: TestClient) -> None:
        assert client.post("/admin/users", json=NEW_CUSTOMER).status_code == 401

    def test_an_admin_can(self, client: TestClient) -> None:
        sign_in(client, ADMIN)
        res = client.post("/admin/users", json=NEW_CUSTOMER)

        assert res.status_code == 201
        assert res.json()["data"]["role"] == "CUSTOMER"


class TestCustomerLinking:
    def test_a_customer_account_must_name_a_company(self, client: TestClient) -> None:
        """Without one they would sign in and see nothing at all."""
        sign_in(client, ADMIN)
        payload = {**NEW_CUSTOMER, "customer_id": None}

        res = client.post("/admin/users", json=payload)

        assert res.status_code == 400
        assert "linked to a customer" in res.json()["detail"]["message"]

    def test_an_unknown_company_is_rejected(self, client: TestClient) -> None:
        sign_in(client, ADMIN)
        res = client.post("/admin/users", json={**NEW_CUSTOMER, "customer_id": 999})
        assert res.status_code == 400

    def test_an_internal_account_may_not_be_linked_to_a_company(
        self, client: TestClient
    ) -> None:
        sign_in(client, ADMIN)
        res = client.post(
            "/admin/users",
            json={
                "email": "someone@dealflow360.com",
                "password": "password123",
                "full_name": "Someone",
                "role": "FINANCE",
                "customer_id": 1,
            },
        )
        assert res.status_code == 400


class TestCreatedAccountWorks:
    def test_the_new_customer_can_sign_in(self, client: TestClient) -> None:
        sign_in(client, ADMIN).post("/admin/users", json=NEW_CUSTOMER)

        res = client.post(
            "/auth/login",
            json={"email": NEW_CUSTOMER["email"], "password": "password123"},
        )

        assert res.status_code == 200
        assert res.json()["data"]["role"] == "CUSTOMER"

    def test_they_only_see_their_own_companys_quotations(
        self, client: TestClient
    ) -> None:
        """Q-1042 belongs to Acme, so a Beta buyer must not reach it.

        Checks the boundary rather than a count: Beta has its own quotations in
        the seed, and the point is that Acme's are not among them.
        """
        sign_in(client, ADMIN).post("/admin/users", json=NEW_CUSTOMER)
        client.post(
            "/auth/login",
            json={"email": NEW_CUSTOMER["email"], "password": "password123"},
        )

        visible = client.get("/portal/quotations").json()["data"]

        assert "q1" not in {q["id"] for q in visible}
        assert client.get("/portal/quotations/q1").status_code == 404

    def test_a_duplicate_email_conflicts(self, client: TestClient) -> None:
        admin = sign_in(client, ADMIN)
        admin.post("/admin/users", json=NEW_CUSTOMER)

        assert admin.post("/admin/users", json=NEW_CUSTOMER).status_code == 409
