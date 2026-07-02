"""DB utils tests — validates bulk_insert and bulk_upsert batching (T-119)."""

import unittest
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestBulkInsert(unittest.TestCase):
    """Test bulk_insert utility."""

    def test_empty_input(self):
        """Returns 0 for empty input."""
        from utils.db_utils import bulk_insert

        mock_conn = MagicMock()
        result = bulk_insert(mock_conn, "test_table", [])
        self.assertEqual(result, 0)
        mock_conn.cursor.assert_not_called()

    def test_single_row(self):
        """Inserts a single row."""
        from utils.db_utils import bulk_insert

        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        rows = [{"name": "test", "score": 42.0}]
        result = bulk_insert(mock_conn, "test_table", rows)

        self.assertEqual(result, 1)
        mock_cursor.executemany.assert_called_once()
        mock_conn.commit.assert_called_once()

    def test_batching(self):
        """Splits into multiple batches when rows > batch_size."""
        from utils.db_utils import bulk_insert

        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        rows = [{"name": f"item_{i}", "score": float(i)} for i in range(5)]
        result = bulk_insert(mock_conn, "test_table", rows, batch_size=2)

        self.assertEqual(result, 5)
        self.assertEqual(mock_cursor.executemany.call_count, 3)  # 2+2+1

    def test_rollback_on_error(self):
        """Rollbacks and re-raises on error."""
        from utils.db_utils import bulk_insert

        mock_cursor = MagicMock()
        mock_cursor.executemany.side_effect = Exception("DB error")
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with self.assertRaises(Exception):
            bulk_insert(mock_conn, "test_table", [{"name": "test"}])

        mock_conn.rollback.assert_called_once()


class TestBulkUpsert(unittest.TestCase):
    """Test bulk_upsert utility."""

    def test_empty_input(self):
        """Returns 0 for empty input."""
        from utils.db_utils import bulk_upsert

        mock_conn = MagicMock()
        result = bulk_upsert(mock_conn, "test_table", [])
        self.assertEqual(result, 0)

    def test_single_row_upsert(self):
        """Upserts a single row with ON DUPLICATE KEY UPDATE."""
        from utils.db_utils import bulk_upsert

        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        rows = [{"entity_name": "OpenAI", "score": 90.0}]
        result = bulk_upsert(mock_conn, "scores", rows, key_columns=["entity_name"])

        self.assertEqual(result, 1)
        sql = mock_cursor.executemany.call_args[0][0]
        self.assertIn("ON DUPLICATE KEY UPDATE", sql)
        self.assertIn("`score` = VALUES(`score`)", sql)

    def test_batching_upsert(self):
        """Splits upserts into batches."""
        from utils.db_utils import bulk_upsert

        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        rows = [{"name": f"item_{i}", "val": i} for i in range(7)]
        result = bulk_upsert(mock_conn, "test_table", rows, batch_size=3)

        self.assertEqual(result, 7)
        self.assertEqual(mock_cursor.executemany.call_count, 3)  # 3+3+1


if __name__ == "__main__":
    unittest.main()
