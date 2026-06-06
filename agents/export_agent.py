"""Export agent — exports data to various formats."""

import logging
from typing import Dict
from agents.base import BaseAgent, AgentResult
import csv
import json
from io import StringIO
from pathlib import Path

_logger = logging.getLogger(__name__)


class ExportAgent(BaseAgent):
    """Exports data to CSV, JSON, or Parquet."""

    @property
    def name(self) -> str:
        return "export"

    def execute(self, upstream_results) -> AgentResult:
        """Export data."""
        try:
            from db.connection import get_connection
            from db import schema

            format_type = self.config.get("format", "csv")
            table = self.config.get("table", "failed_startups")
            output_path = self.config.get("output_path", "data/export")

            conn = get_connection()
            schema.init_schema(conn)
            cursor = conn.cursor()

            cursor.execute(f"SELECT * FROM {table} LIMIT 1000")
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            cursor.close()
            conn.close()

            Path(output_path).mkdir(parents=True, exist_ok=True)

            if format_type == "csv":
                filepath = f"{output_path}/{table}.csv"
                with open(filepath, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(columns)
                    writer.writerows(rows)
            elif format_type == "json":
                filepath = f"{output_path}/{table}.json"
                with open(filepath, "w") as f:
                    json.dump([dict(r) for r in rows], f, indent=2, default=str)
            else:
                return AgentResult(
                    agent_name=self.name,
                    status="failed",
                    errors=[f"Unsupported format: {format_type}"],
                )

            return AgentResult(
                agent_name=self.name,
                status="success",
                data={"exported": len(rows), "format": format_type, "path": filepath},
            )
        except Exception as e:
            return AgentResult(
                agent_name=self.name,
                status="failed",
                errors=[str(e)],
            )
