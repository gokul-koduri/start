"""Tests for the parallel task spawner."""

import unittest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestParallelSpawner(unittest.TestCase):
    """Test parallel task spawning, tracking, and completion."""

    def test_import(self):
        """Test parallel_spawner can be imported."""
        from agents.parallel_spawner import (
            spawn_task,
            update_task_status,
            record_artifacts,
            print_status,
        )

        self.assertTrue(callable(spawn_task))
        self.assertTrue(callable(update_task_status))
        self.assertTrue(callable(record_artifacts))
        self.assertTrue(callable(print_status))

    def test_status_enum(self):
        """Test TaskStatus enum values."""
        from agents.parallel_spawner import TaskStatus

        self.assertEqual(TaskStatus.QUEUED.value, "queued")
        self.assertEqual(TaskStatus.DONE.value, "done")
        self.assertEqual(TaskStatus.FAILED.value, "failed")

    def test_task_type_enum(self):
        """Test TaskType enum values."""
        from agents.parallel_spawner import TaskType

        self.assertEqual(TaskType.BUILD.value, "build")
        self.assertEqual(TaskType.FIX.value, "fix")
        self.assertEqual(TaskType.REFACTOR.value, "refactor")

    @patch("agents.parallel_spawner.get_connection")
    def test_spawn_task_inserts_row(self, mock_conn):
        """Test spawn_task creates a DB row."""
        from agents.parallel_spawner import spawn_task

        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 1
        mock_cursor.fetchone.return_value = None  # No existing task
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value.cursor.return_value.__enter__ = MagicMock(
            return_value=mock_cursor
        )
        mock_conn.return_value.cursor.return_value.__exit__ = MagicMock(
            return_value=False
        )

        # Mock _ensure_tables
        with patch("agents.parallel_spawner._ensure_tables"):
            task_id = spawn_task(
                name="email-queue",
                description="Build email queue with templates and retry",
                task_type="build",
                priority="P1",
            )

        self.assertEqual(task_id, 1)
        # Verify INSERT was called
        insert_calls = [
            c
            for c in mock_cursor.execute.call_args_list
            if "INSERT INTO parallel_tasks" in str(c)
        ]
        self.assertEqual(len(insert_calls), 1)

    @patch("agents.parallel_spawner.get_connection")
    def test_spawn_duplicate_active_raises(self, mock_conn):
        """Test spawning a task with same name as active task raises ValueError."""
        from agents.parallel_spawner import spawn_task

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": 1, "status": "building"}
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value.cursor.return_value.__enter__ = MagicMock(
            return_value=mock_cursor
        )
        mock_conn.return_value.cursor.return_value.__exit__ = MagicMock(
            return_value=False
        )

        with patch("agents.parallel_spawner._ensure_tables"):
            with self.assertRaises(ValueError) as ctx:
                spawn_task(name="email-queue", description="x")
            self.assertIn("already exists", str(ctx.exception))

    @patch("agents.parallel_spawner.get_connection")
    def test_spawn_after_done_allowed(self, mock_conn):
        """Test spawning a task with same name as done task is allowed."""
        from agents.parallel_spawner import spawn_task

        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 2
        # First call: check existing → found done task
        # Second call: insert new
        mock_cursor.fetchone.return_value = {"id": 1, "status": "done"}
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value.cursor.return_value.__enter__ = MagicMock(
            return_value=mock_cursor
        )
        mock_conn.return_value.cursor.return_value.__exit__ = MagicMock(
            return_value=False
        )

        with patch("agents.parallel_spawner._ensure_tables"):
            task_id = spawn_task(name="email-queue", description="v2")
        self.assertEqual(task_id, 2)

    @patch("agents.parallel_spawner.get_connection")
    def test_update_status(self, mock_conn):
        """Test update_task_status changes status and logs."""
        from agents.parallel_spawner import update_task_status

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value.cursor.return_value.__enter__ = MagicMock(
            return_value=mock_cursor
        )
        mock_conn.return_value.cursor.return_value.__exit__ = MagicMock(
            return_value=False
        )

        update_task_status(1, "building", message="Started coding")
        # Should have UPDATE + INSERT (log)
        self.assertTrue(mock_cursor.execute.call_count >= 2)

    @patch("agents.parallel_spawner.get_connection")
    def test_record_artifacts(self, mock_conn):
        """Test record_artifacts saves files and test counts."""
        from agents.parallel_spawner import record_artifacts

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "files_created": "[]",
            "files_modified": "[]",
            "tests_added": 0,
            "tests_passing": 0,
        }
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value.cursor.return_value.__enter__ = MagicMock(
            return_value=mock_cursor
        )
        mock_conn.return_value.cursor.return_value.__exit__ = MagicMock(
            return_value=False
        )

        record_artifacts(
            1,
            files_created=["utils/email_queue.py", "agents/email_worker.py"],
            files_modified=["db/schema.py", "agents/report_generator_agent.py"],
            tests_added=19,
            tests_passing=19,
        )
        update_calls = [
            c
            for c in mock_cursor.execute.call_args_list
            if "UPDATE parallel_tasks" in str(c)
        ]
        self.assertEqual(len(update_calls), 1)


class TestParallelSpawnerOrchestrated(unittest.TestCase):
    """Test the orchestrator agent wrapper."""

    def test_orchestrated_wrapper_exists(self):
        """Test OrchestratedParallelSpawner can be imported."""
        from agents.parallel_spawner import OrchestratedParallelSpawner

        wrapper = OrchestratedParallelSpawner()
        self.assertEqual(wrapper.name, "parallel_spawner")
        self.assertTrue(wrapper.enabled)

    @patch("agents.parallel_spawner.list_tasks")
    def test_orchestrated_no_tasks(self, mock_list):
        """Test wrapper returns success when no tasks queued."""
        from agents.parallel_spawner import OrchestratedParallelSpawner

        mock_list.return_value = []

        wrapper = OrchestratedParallelSpawner()
        result = wrapper.run()
        self.assertEqual(result.status, "success")
        self.assertIn("No queued", result.data["message"])

    @patch("agents.parallel_spawner.list_tasks")
    def test_orchestrated_with_tasks(self, mock_list):
        """Test wrapper reports queued tasks."""
        from agents.parallel_spawner import OrchestratedParallelSpawner

        mock_list.return_value = [
            {"task_name": "email-queue", "priority": "P1"},
            {"task_name": "auth-fix", "priority": "P0"},
        ]

        wrapper = OrchestratedParallelSpawner()
        result = wrapper.run()
        self.assertEqual(result.status, "success")
        self.assertEqual(result.data["queued_tasks"], 2)


class TestParallelTasksSchema(unittest.TestCase):
    """Test that schema includes parallel_tasks tables."""

    def test_tables_exist_in_ensure(self):
        """Test parallel_tasks table SQL is defined."""
        from agents.parallel_spawner import (
            _PARALLEL_TASKS_TABLE,
            _PARALLEL_TASK_LOG_TABLE,
        )

        self.assertIn("parallel_tasks", _PARALLEL_TASKS_TABLE)
        self.assertIn("parallel_task_log", _PARALLEL_TASK_LOG_TABLE)
        self.assertIn("task_name", _PARALLEL_TASKS_TABLE)
        self.assertIn("status", _PARALLEL_TASKS_TABLE)
        self.assertIn("files_created", _PARALLEL_TASKS_TABLE)
        self.assertIn("wall_clock_minutes", _PARALLEL_TASKS_TABLE)


class TestRunTests(unittest.TestCase):
    """Test the test runner utility."""

    def test_run_tests_function_exists(self):
        """Test run_tests is callable."""
        from agents.parallel_spawner import run_tests

        self.assertTrue(callable(run_tests))


if __name__ == "__main__":
    unittest.main()
