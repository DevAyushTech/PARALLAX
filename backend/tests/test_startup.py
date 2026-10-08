import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError

from app import db
from app.agents import AgentOutputError
from app.config import Settings
from app.main import invalid_agent_output, lifespan


class StartupReliabilityTests(unittest.IsolatedAsyncioTestCase):
    def test_env_file_loads_and_environment_takes_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text(
                "PARALLAX_CORS_ORIGINS=http://127.0.0.1:5173\n"
                "PARALLAX_DECISION_GATE__FRESHNESS_SECONDS=30\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                settings = Settings(_env_file=env_file)
                self.assertEqual(settings.cors_origin_list, ["http://127.0.0.1:5173"])
                self.assertEqual(settings.decision_gate.freshness_seconds, 30)
                with patch.dict(os.environ, {"PARALLAX_DECISION_GATE__FRESHNESS_SECONDS": "60"}):
                    self.assertEqual(Settings(_env_file=env_file).decision_gate.freshness_seconds, 60)

    def test_legacy_evidence_upgrade_is_idempotent_and_preserves_data(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        try:
            with engine.begin() as connection:
                connection.execute(text(
                    "CREATE TABLE evidence (id TEXT PRIMARY KEY, content TEXT, timestamp DATETIME)"
                ))
                connection.execute(text(
                    "INSERT INTO evidence VALUES ('legacy', 'preserve this report', '2026-01-01 12:00:00')"
                ))
            with patch.object(db, "engine", engine):
                db._upgrade_existing_sqlite_schema()
                db._upgrade_existing_sqlite_schema()
            self.assertIn("created_at", {column["name"] for column in inspect(engine).get_columns("evidence")})
            with engine.connect() as connection:
                row = connection.execute(text("SELECT content, created_at FROM evidence")).one()
            self.assertEqual(tuple(row), ("preserve this report", "2026-01-01 12:00:00"))
        finally:
            engine.dispose()

    async def test_startup_database_error_is_actionable(self) -> None:
        error = OperationalError("CREATE TABLE", {}, RuntimeError("unwritable"))
        with patch("app.main.init_db", side_effect=error):
            with self.assertRaisesRegex(RuntimeError, "database directory exists and is writable"):
                async with lifespan(None):
                    pass

    async def test_invalid_agent_output_error_is_json_without_raw_payload(self) -> None:
        response = await invalid_agent_output(None, AgentOutputError("sensitive raw output"))
        self.assertEqual(response.status_code, 502)
        payload = json.loads(response.body)
        self.assertIn("previous decision is unchanged", payload["detail"])
        self.assertNotIn("sensitive raw output", payload["detail"])


if __name__ == "__main__":
    unittest.main()
