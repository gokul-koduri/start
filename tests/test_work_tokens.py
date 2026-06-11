"""Tests for the work token system — blocked work that auto-releases."""

import unittest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestWorkTokens(unittest.TestCase):
    """Test the work token lifecycle."""

    def test_import(self):
        """Test work_tokens module can be imported."""
        from utils.work_tokens import (
            create_token,
            release_completed_blockers,
            claim_token,
        )

        self.assertTrue(callable(create_token))
        self.assertTrue(callable(release_completed_blockers))
        self.assertTrue(callable(claim_token))

    def test_token_status_enum(self):
        """Test TokenStatus values."""
        from utils.work_tokens import TokenStatus

        self.assertEqual(TokenStatus.BLOCKED.value, "blocked")
        self.assertEqual(TokenStatus.READY.value, "ready")
        self.assertEqual(TokenStatus.CLAIMED.value, "claimed")
        self.assertEqual(TokenStatus.DONE.value, "done")
        self.assertEqual(TokenStatus.EXPIRED.value, "expired")

    def test_create_token_requires_blockers(self):
        """Test that create_token raises ValueError without blockers."""
        from utils.work_tokens import create_token

        with self.assertRaises(ValueError) as ctx:
            create_token(name="test", description="x", blocked_by=[])
        self.assertIn("at least one", str(ctx.exception))

    @patch("utils.work_tokens.get_connection")
    def test_create_token_blocked(self, mock_conn):
        """Test creating a token that starts as blocked."""
        from utils.work_tokens import create_token

        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 1
        mock_cursor.fetchone.return_value = {"id": 2, "status": "building"}
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value.cursor.return_value.__enter__ = MagicMock(
            return_value=mock_cursor
        )
        mock_conn.return_value.cursor.return_value.__exit__ = MagicMock(
            return_value=False
        )

        with patch("utils.work_tokens._ensure_tables"):
            token_id = create_token(
                name="wire-email-templates",
                description="Wire email templates into worker",
                blocked_by=[2],
                created_by=3,
                priority="P1",
            )

        self.assertEqual(token_id, 1)
        # Should have INSERT INTO work_tokens + INSERT INTO token_blockers + INSERT INTO token_log
        insert_calls = [
            c for c in mock_cursor.execute.call_args_list if "INSERT" in str(c)
        ]
        self.assertEqual(len(insert_calls), 3)

    @patch("utils.work_tokens.get_connection")
    def test_create_token_ready_if_all_done(self, mock_conn):
        """Test token starts as 'ready' if all blockers are already done."""
        from utils.work_tokens import create_token

        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 5
        # Blocker task is already done
        mock_cursor.fetchone.side_effect = [
            {"id": 2, "status": "done"},  # blocker check
        ]
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value.cursor.return_value.__enter__ = MagicMock(
            return_value=mock_cursor
        )
        mock_conn.return_value.cursor.return_value.__exit__ = MagicMock(
            return_value=False
        )

        with patch("utils.work_tokens._ensure_tables"):
            token_id = create_token(
                name="post-schema-work",
                description="Work after schema is done",
                blocked_by=[2],
            )

        self.assertEqual(token_id, 5)
        # Check that initial status was "ready" (INSERT is after the SELECT checks)
        insert_calls = [
            c
            for c in mock_cursor.execute.call_args_list
            if "INSERT INTO work_tokens" in str(c)
        ]
        self.assertEqual(len(insert_calls), 1)
        self.assertIn("ready", str(insert_calls[0]))

    @patch("utils.work_tokens.get_connection")
    def test_release_completed_blockers(self, mock_conn):
        """Test that completing a task releases its blocked tokens."""
        from utils.work_tokens import release_completed_blockers

        mock_cursor = MagicMock()
        # 1) UPDATE token_blockers (mark satisfied)
        # 2) SELECT tokens where all blockers satisfied
        # 3) For each: UPDATE work_tokens + INSERT token_log
        mock_cursor.fetchall.return_value = [
            {"id": 1, "token_name": "wire-email-templates"},
        ]
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value.cursor.return_value.__enter__ = MagicMock(
            return_value=mock_cursor
        )
        mock_conn.return_value.cursor.return_value.__exit__ = MagicMock(
            return_value=False
        )

        released = release_completed_blockers(task_id=2)

        self.assertEqual(released, [1])

    @patch("utils.work_tokens.get_connection")
    def test_release_nothing_if_none_blocked(self, mock_conn):
        """Test release returns empty when no tokens are blocked."""
        from utils.work_tokens import release_completed_blockers

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []  # No tokens to release
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value.cursor.return_value.__enter__ = MagicMock(
            return_value=mock_cursor
        )
        mock_conn.return_value.cursor.return_value.__exit__ = MagicMock(
            return_value=False
        )

        released = release_completed_blockers(task_id=99)
        self.assertEqual(released, [])

    @patch("utils.work_tokens.get_connection")
    def test_claim_token(self, mock_conn):
        """Test claiming a ready token."""
        from utils.work_tokens import claim_token

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"status": "ready"}
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value.cursor.return_value.__enter__ = MagicMock(
            return_value=mock_cursor
        )
        mock_conn.return_value.cursor.return_value.__exit__ = MagicMock(
            return_value=False
        )

        claim_token(1, claimed_by=3)

        update_calls = [
            c
            for c in mock_cursor.execute.call_args_list
            if "UPDATE work_tokens" in str(c)
        ]
        self.assertEqual(len(update_calls), 1)
        self.assertIn("claimed", str(update_calls[0]))

    @patch("utils.work_tokens.get_connection")
    def test_claim_non_ready_raises(self, mock_conn):
        """Test that claiming a non-ready token raises ValueError."""
        from utils.work_tokens import claim_token

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"status": "blocked"}
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value.cursor.return_value.__enter__ = MagicMock(
            return_value=mock_cursor
        )
        mock_conn.return_value.cursor.return_value.__exit__ = MagicMock(
            return_value=False
        )

        with self.assertRaises(ValueError) as ctx:
            claim_token(1, claimed_by=3)
        self.assertIn("not 'ready'", str(ctx.exception))

    @patch("utils.work_tokens.get_connection")
    def test_complete_token(self, mock_conn):
        """Test completing a claimed token with artifacts."""
        from utils.work_tokens import complete_token

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"status": "claimed"}
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value.cursor.return_value.__enter__ = MagicMock(
            return_value=mock_cursor
        )
        mock_conn.return_value.cursor.return_value.__exit__ = MagicMock(
            return_value=False
        )

        complete_token(
            1,
            result="Templates wired into worker",
            files_created=["templates/email/worker.html"],
            files_modified=["agents/email_worker.py"],
            tests_added=5,
            tests_passing=5,
        )

        update_calls = [
            c
            for c in mock_cursor.execute.call_args_list
            if "UPDATE work_tokens" in str(c)
        ]
        self.assertEqual(len(update_calls), 1)
        self.assertIn("done", str(update_calls[0]))

    @patch("utils.work_tokens.get_connection")
    def test_complete_non_claimed_raises(self, mock_conn):
        """Test that completing a non-claimed token raises ValueError."""
        from utils.work_tokens import complete_token

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"status": "ready"}
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value.cursor.return_value.__enter__ = MagicMock(
            return_value=mock_cursor
        )
        mock_conn.return_value.cursor.return_value.__exit__ = MagicMock(
            return_value=False
        )

        with self.assertRaises(ValueError) as ctx:
            complete_token(1, result="done")
        self.assertIn("not 'claimed'", str(ctx.exception))

    @patch("utils.work_tokens.get_connection")
    def test_expire_token(self, mock_conn):
        """Test expiring a token."""
        from utils.work_tokens import expire_token

        mock_cursor = MagicMock()
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value.cursor.return_value.__enter__ = MagicMock(
            return_value=mock_cursor
        )
        mock_conn.return_value.cursor.return_value.__exit__ = MagicMock(
            return_value=False
        )

        expire_token(1, reason="No longer needed")
        update_calls = [
            c for c in mock_cursor.execute.call_args_list if "expired" in str(c)
        ]
        self.assertTrue(len(update_calls) >= 1)


class TestTokenQueries(unittest.TestCase):
    """Test token query functions."""

    @patch("utils.work_tokens.get_connection")
    def test_get_token_with_blockers(self, mock_conn):
        """Test get_token returns token with blockers."""
        from utils.work_tokens import get_token

        mock_cursor = MagicMock()
        token_data = {"id": 1, "token_name": "test", "status": "blocked"}
        blocker_data = [
            {
                "id": 1,
                "blocking_task_id": 2,
                "satisfied": 0,
                "task_name": "schema-change",
                "task_status": "building",
            },
        ]
        mock_cursor.fetchone.side_effect = [token_data]
        mock_cursor.fetchall.return_value = blocker_data
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value.cursor.return_value.__enter__ = MagicMock(
            return_value=mock_cursor
        )
        mock_conn.return_value.cursor.return_value.__exit__ = MagicMock(
            return_value=False
        )

        with patch("utils.work_tokens._ensure_tables"):
            token = get_token(1)

        self.assertIsNotNone(token)
        self.assertEqual(token["token_name"], "test")
        self.assertEqual(len(token["blockers"]), 1)
        self.assertEqual(token["blockers"][0]["task_name"], "schema-change")

    @patch("utils.work_tokens.get_connection")
    def test_list_tokens_by_status(self, mock_conn):
        """Test listing tokens filtered by status."""
        from utils.work_tokens import list_tokens

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"id": 1, "token_name": "t1", "status": "ready"},
            {"id": 2, "token_name": "t2", "status": "ready"},
        ]
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value.cursor.return_value.__enter__ = MagicMock(
            return_value=mock_cursor
        )
        mock_conn.return_value.cursor.return_value.__exit__ = MagicMock(
            return_value=False
        )

        with patch("utils.work_tokens._ensure_tables"):
            tokens = list_tokens(status="ready")

        self.assertEqual(len(tokens), 2)

    @patch("utils.work_tokens.get_connection")
    def test_token_stats(self, mock_conn):
        """Test token_stats returns counts."""
        from utils.work_tokens import token_stats

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"status": "blocked", "cnt": 3},
            {"status": "ready", "cnt": 1},
            {"status": "done", "cnt": 5},
        ]
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value.cursor.return_value.__enter__ = MagicMock(
            return_value=mock_cursor
        )
        mock_conn.return_value.cursor.return_value.__exit__ = MagicMock(
            return_value=False
        )

        with patch("utils.work_tokens._ensure_tables"):
            stats = token_stats()

        self.assertEqual(stats["blocked"], 3)
        self.assertEqual(stats["ready"], 1)
        self.assertEqual(stats["done"], 5)
        self.assertEqual(stats["claimed"], 0)


class TestTokenLifecycleIntegration(unittest.TestCase):
    """Test the full token lifecycle: blocked → ready → claimed → done."""

    def test_lifecycle_constants(self):
        """Test all status transitions are defined."""
        from utils.work_tokens import TokenStatus

        statuses = [s.value for s in TokenStatus]
        self.assertIn("blocked", statuses)
        self.assertIn("ready", statuses)
        self.assertIn("claimed", statuses)
        self.assertIn("done", statuses)
        self.assertIn("expired", statuses)

    def test_tables_defined(self):
        """Test DB table SQL is complete."""
        from utils.work_tokens import (
            _WORK_TOKENS_TABLE,
            _TOKEN_BLOCKERS_TABLE,
            _TOKEN_LOG_TABLE,
        )

        self.assertIn("work_tokens", _WORK_TOKENS_TABLE)
        self.assertIn("token_blockers", _TOKEN_BLOCKERS_TABLE)
        self.assertIn("token_log", _TOKEN_LOG_TABLE)
        # Key columns
        self.assertIn("status", _WORK_TOKENS_TABLE)
        self.assertIn("blocking_task_id", _TOKEN_BLOCKERS_TABLE)
        self.assertIn("satisfied", _TOKEN_BLOCKERS_TABLE)
        self.assertIn("event", _TOKEN_LOG_TABLE)


class TestParallelSpawnerTokenIntegration(unittest.TestCase):
    """Test that parallel spawner properly integrates tokens."""

    def test_imports_work(self):
        """Test parallel_spawner can import work_tokens."""
        from agents.parallel_spawner import _create_token, release_completed_blockers

        self.assertTrue(callable(_create_token))
        self.assertTrue(callable(release_completed_blockers))


if __name__ == "__main__":
    unittest.main()
