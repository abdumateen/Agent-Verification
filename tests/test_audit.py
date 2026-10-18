"""SQLite audit chain behavior and tampering checks."""

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from verifygate.audit import append_event, list_events, verify_ledger


class AuditTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / "audit.sqlite"

    def test_append_and_listing(self):
        first = append_event(self.path, {"run_id": "a", "step": 1})
        second = append_event(self.path, {"run_id": "b", "step": 2})
        third = append_event(self.path, {"run_id": "a", "step": 3})
        self.assertEqual(first["seq"], 1)
        self.assertEqual(second["prev_hash"], first["hash"])
        self.assertTrue(verify_ledger(self.path))
        self.assertEqual(list_events(self.path, "a"), [third, first])
        self.assertEqual(list_events(self.path, limit=1), [third])

    def test_rollback_on_invalid_chain(self):
        append_event(self.path, {"step": 1})
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("UPDATE events SET event = ? WHERE seq = 1", ('{"step":9}',))
        with self.assertRaises(ValueError):
            append_event(self.path, {"step": 2})
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM events").fetchone()[0], 1)

    def test_transaction_failure_rolls_back(self):
        append_event(self.path, {"step": 1})
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("CREATE TRIGGER reject_insert BEFORE INSERT ON events BEGIN SELECT RAISE(ABORT, 'blocked'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            append_event(self.path, {"step": 2})
        self.assertTrue(verify_ledger(self.path))
        self.assertEqual(len(list_events(self.path)), 1)

    def test_tampering(self):
        for operation in ("modification", "interior deletion", "reorder", "sequence", "hash"):
            with self.subTest(operation=operation):
                path = self.path.with_name(operation + ".sqlite")
                for step in range(1, 4):
                    append_event(path, {"step": step})
                with closing(sqlite3.connect(path)) as db, db:
                    if operation == "modification":
                        db.execute("UPDATE events SET event = ? WHERE seq = 2", ('{"step":42}',))
                    elif operation == "interior deletion":
                        db.execute("DELETE FROM events WHERE seq = 2")
                    elif operation == "reorder":
                        db.execute("UPDATE events SET seq = -1 WHERE seq = 2")
                    elif operation == "sequence":
                        db.execute("UPDATE events SET seq = 7 WHERE seq = 3")
                    else:
                        db.execute("UPDATE events SET hash = ? WHERE seq = 2", ("0" * 64,))
                self.assertFalse(verify_ledger(path))
                with self.assertRaises(ValueError):
                    append_event(path, {"step": 4})


if __name__ == "__main__":
    unittest.main()
