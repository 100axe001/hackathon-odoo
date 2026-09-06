"""Deal Health: the three detectors, and the actions on a flag.

All advisory. None of this influences approval routing, and there is a test
below that says so.
"""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.utils.anomaly import (
    anomaly_util_baseline,
    anomaly_util_is_anomalous,
    anomaly_util_z_score,
)

MANAGER = {"email": "manager@dealflow360.com", "password": "dealflow123"}


def sign_in(client: TestClient, who: dict) -> TestClient:
    client.post("/auth/login", json=who)
    return client


class TestAnomalyBaseline:
    """The constants here were wrong in the first draft; these pin the fixes."""

    def test_the_worked_example_from_the_spec(self) -> None:
        history = [Decimal(v) for v in (4, 6, 8, 8, 10, 12)]
        mean, spread = anomaly_util_baseline(history)

        assert mean == Decimal("8")
        assert round(anomaly_util_z_score(Decimal("22"), mean, spread), 2) == Decimal(
            "4.95"
        )

    def test_a_consistent_rep_does_not_false_flag_on_an_ordinary_discount(
        self,
    ) -> None:
        """Without a floor on the spread this scored 3.54 and was flagged."""
        history = [Decimal(v) for v in (5, 5, 6, 5, 6)]
        mean, spread = anomaly_util_baseline(history)

        z = anomaly_util_z_score(Decimal("7"), mean, spread)
        assert not anomaly_util_is_anomalous(z)

    def test_a_thin_history_falls_back_to_the_platform_baseline(self) -> None:
        """Three points cannot estimate a spread."""
        mean, spread = anomaly_util_baseline([Decimal("8"), Decimal("9")])
        assert (mean, spread) == (Decimal("8.0"), Decimal("4.0"))

    def test_only_unusually_high_discounts_count(self) -> None:
        """A discount far below the average costs the company nothing."""
        history = [Decimal(v) for v in (10, 12, 14, 11, 13)]
        mean, spread = anomaly_util_baseline(history)

        assert not anomaly_util_is_anomalous(
            anomaly_util_z_score(Decimal("0"), mean, spread)
        )


class TestBoard:
    @pytest.fixture
    def board(self, client: TestClient) -> dict:
        return sign_in(client, MANAGER).get("/deal-health").json()["data"]

    def test_all_three_categories_are_reported(self, board: dict) -> None:
        assert set(board) == {"stalled", "anomalies", "slippage"}

    def test_a_quotation_untouched_for_twelve_days_is_stalled(
        self, board: dict
    ) -> None:
        assert any("12 days" in row["issue"] for row in board["stalled"])

    def test_an_outlier_discount_is_flagged_against_the_reps_own_average(
        self, board: dict
    ) -> None:
        """The wireframe's wording: "Discount 22% vs avg 8%"."""
        assert board["anomalies"]
        issue = board["anomalies"][0]["issue"]
        assert "vs avg" in issue
        assert board["anomalies"][0]["severity"] == "HIGH"

    def test_a_late_expected_date_is_slippage(self, board: dict) -> None:
        assert any("after the promised date" in r["issue"] for r in board["slippage"])

    def test_every_flag_links_back_to_its_quotation(self, board: dict) -> None:
        """PS 4 B9: clicking an alert opens the related quotation."""
        rows = board["stalled"] + board["anomalies"] + board["slippage"]
        assert rows
        assert all(row["quotation_id"].startswith("q") for row in rows)


class TestActions:
    def test_escalating_records_the_action(self, client: TestClient) -> None:
        board = sign_in(client, MANAGER).get("/deal-health").json()["data"]
        flag_id = board["anomalies"][0]["id"]

        res = client.post(f"/deal-health/{flag_id}/escalate")

        assert res.status_code == 200
        assert res.json()["data"]["action"] == "ESCALATED"

    def test_an_action_survives_the_board_being_recomputed(
        self, client: TestClient
    ) -> None:
        """Flags are derived, but a human decision on one must not be erased."""
        mgr = sign_in(client, MANAGER)
        flag_id = mgr.get("/deal-health").json()["data"]["anomalies"][0]["id"]
        mgr.post(f"/deal-health/{flag_id}/nudge")

        after = mgr.get("/deal-health").json()["data"]["anomalies"][0]

        assert after["action"] == "NUDGED"

    def test_an_unknown_flag_is_not_found(self, client: TestClient) -> None:
        sign_in(client, MANAGER)
        assert client.post("/deal-health/f9999/escalate").status_code == 404

    def test_a_customer_cannot_see_the_board(self, client: TestClient) -> None:
        client.post(
            "/auth/login",
            json={"email": "customer@acmecorp.com", "password": "dealflow123"},
        )
        assert client.get("/deal-health").status_code == 403


class TestSeparationFromApproval:
    def test_deal_health_does_not_change_the_risk_level(
        self, client: TestClient
    ) -> None:
        """Advisory means advisory: scoring the board must not route anything."""
        rep = sign_in(
            client, {"email": "rep@dealflow360.com", "password": "dealflow123"}
        )
        before = rep.get("/quotations/q1").json()["data"]

        sign_in(client, MANAGER).get("/deal-health")

        after = (
            sign_in(client, {"email": "rep@dealflow360.com", "password": "dealflow123"})
            .get("/quotations/q1")
            .json()["data"]
        )

        assert [ln["status"] for ln in before["lines"]] == [
            ln["status"] for ln in after["lines"]
        ]
