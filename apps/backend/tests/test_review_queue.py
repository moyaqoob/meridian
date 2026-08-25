"""Review queue idempotency tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from models.tables import Review
from services.review_queue import enqueue_review_job, find_existing_review


def _review(*, status: str, review_id: str = "rev-1", pr_id: str = "pr-1") -> Review:
    return Review(
        id=review_id,
        pr_id=pr_id,
        head_sha="abc123",
        status=status,
    )


def test_enqueue_skips_complete_review(mock_db: MagicMock) -> None:
    complete = _review(status="complete")

    with (
        patch(
            "services.review_queue.find_existing_review",
            return_value=complete,
        ),
        patch("services.review_queue.review_queue") as queue,
    ):
        result = enqueue_review_job(
            mock_db,
            repo_id="repo-1",
            pr_number=3,
            head_sha="abc123",
        )

    assert result.status == "exists"
    assert result.review_id == "rev-1"
    queue.return_value.enqueue.assert_not_called()


def test_enqueue_skips_running_review(mock_db: MagicMock) -> None:
    running = _review(status="running")

    with (
        patch(
            "services.review_queue.find_existing_review",
            return_value=running,
        ),
        patch("services.review_queue.review_queue") as queue,
    ):
        result = enqueue_review_job(
            mock_db,
            repo_id="repo-1",
            pr_number=3,
            head_sha="abc123",
        )

    assert result.status == "running"
    assert result.review_id == "rev-1"
    queue.return_value.enqueue.assert_not_called()


def test_enqueue_retries_failed_review(mock_db: MagicMock) -> None:
    failed = _review(status="error")

    with (
        patch(
            "services.review_queue.find_existing_review",
            return_value=failed,
        ),
        patch("services.review_queue.review_queue") as queue,
    ):
        result = enqueue_review_job(
            mock_db,
            repo_id="repo-1",
            pr_number=3,
            head_sha="abc123",
        )

    assert result.status == "queued"
    assert result.review_id == "rev-1"
    queue.return_value.enqueue.assert_called_once()


def test_find_existing_review_uses_pr_join(mock_db: MagicMock) -> None:
    mock_db.query.return_value.join.return_value.filter.return_value.one_or_none.return_value = (
        _review(status="complete")
    )

    row = find_existing_review(
        mock_db,
        repo_id="repo-1",
        pr_number=3,
        head_sha="abc123",
    )

    assert row is not None
    assert row.id == "rev-1"
    mock_db.query.return_value.join.assert_called_once()
