"""Authentication behaviour."""

from fastapi.testclient import TestClient

REP = {"email": "rep@dealflow360.com", "password": "dealflow123"}


class TestLogin:
    def test_correct_credentials_return_the_user_and_set_a_cookie(
        self, client: TestClient
    ) -> None:
        res = client.post("/auth/login", json=REP)

        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert body["data"]["role"] == "SALES_REP"
        assert "dealflow_session" in res.cookies

    def test_the_session_cookie_is_http_only(self, client: TestClient) -> None:
        """A page script must not be able to read the token."""
        res = client.post("/auth/login", json=REP)
        assert "httponly" in res.headers["set-cookie"].lower()

    def test_a_wrong_password_is_rejected(self, client: TestClient) -> None:
        res = client.post("/auth/login", json={**REP, "password": "not-the-password"})
        assert res.status_code == 401

    def test_an_unknown_email_gives_the_same_message_as_a_wrong_password(
        self, client: TestClient
    ) -> None:
        """Differing messages would let an attacker enumerate accounts."""
        wrong_password = client.post(
            "/auth/login", json={**REP, "password": "nope"}
        ).json()
        unknown_email = client.post(
            "/auth/login",
            json={"email": "nobody@nowhere.com", "password": "nope"},
        ).json()

        assert wrong_password == unknown_email


class TestSession:
    def test_me_requires_a_cookie(self, client: TestClient) -> None:
        assert client.get("/auth/me").status_code == 401

    def test_me_returns_the_signed_in_user(self, rep_client: TestClient) -> None:
        body = rep_client.get("/auth/me").json()
        assert body["data"]["email"] == "rep@dealflow360.com"

    def test_logout_ends_the_session(self, rep_client: TestClient) -> None:
        assert rep_client.post("/auth/logout").status_code == 200
        assert rep_client.get("/auth/me").status_code == 401

    def test_a_tampered_token_is_rejected(self, rep_client: TestClient) -> None:
        """The signature is what makes the claims trustworthy."""
        rep_client.cookies.set("dealflow_session", "not.a.real.token")
        assert rep_client.get("/auth/me").status_code == 401


class TestSignup:
    NEW = {
        "email": "brand.new@dealflow360.com",
        "password": "long-enough-password",
        "full_name": "Brand New",
    }

    def test_signup_creates_an_account_and_signs_it_in(
        self, client: TestClient
    ) -> None:
        res = client.post("/auth/signup", json=self.NEW)

        assert res.status_code == 201
        assert "dealflow_session" in res.cookies
        assert client.get("/auth/me").json()["data"]["name"] == "Brand New"

    def test_self_signup_can_never_choose_a_privileged_role(
        self, client: TestClient
    ) -> None:
        """Otherwise anyone could register as the approver of their own discounts."""
        res = client.post("/auth/signup", json={**self.NEW, "role": "FINANCE"})
        assert res.json()["data"]["role"] == "SALES_REP"

    def test_a_duplicate_email_conflicts(self, client: TestClient) -> None:
        client.post("/auth/signup", json=self.NEW)
        assert client.post("/auth/signup", json=self.NEW).status_code == 409

    def test_a_short_password_is_rejected(self, client: TestClient) -> None:
        res = client.post("/auth/signup", json={**self.NEW, "password": "short"})
        assert res.status_code == 422
