"""Repository for valuation model tables (user_data.db).

See phase0b_database_schema.md — Tables #4-10:
  models, dcf_assumptions, ddm_assumptions, revbased_assumptions,
  comps_assumptions, model_outputs, model_versions
"""

from datetime import datetime, timezone

from db.connection import DatabaseConnection


class ModelRepo:

    def __init__(self, db: DatabaseConnection):
        self.db = db

    # --- models table ---

    async def get_model(self, model_id: int) -> dict | None:
        return await self.db.fetchone("SELECT * FROM models WHERE id = ?", (model_id,))

    async def get_models_for_ticker(self, ticker: str) -> list[dict]:
        return await self.db.fetchall(
            "SELECT * FROM models WHERE ticker = ? ORDER BY model_type",
            (ticker.upper(),),
        )

    async def get_model_by_ticker_type(self, ticker: str, model_type: str) -> dict | None:
        return await self.db.fetchone(
            "SELECT * FROM models WHERE ticker = ? AND model_type = ?",
            (ticker.upper(), model_type),
        )

    async def get_or_create_model(self, ticker: str, model_type: str) -> dict:
        """Get existing model for ticker+type, or create one."""
        existing = await self.get_model_by_ticker_type(ticker, model_type)
        if existing:
            return existing
        return await self.create_model({
            "ticker": ticker.upper(),
            "model_type": model_type,
        })

    async def create_model(self, data: dict) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        cursor = await self.db.execute(
            """INSERT INTO models
               (ticker, model_type, auto_detection_score, auto_detection_confidence,
                auto_detection_confidence_pct, auto_detection_reasoning,
                is_recommended, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["ticker"].upper(),
                data["model_type"],
                data.get("auto_detection_score"),
                data.get("auto_detection_confidence"),
                data.get("auto_detection_confidence_pct"),
                data.get("auto_detection_reasoning"),
                data.get("is_recommended", 0),
                now,
            ),
        )
        await self.db.commit()
        return await self.get_model(cursor.lastrowid)

    async def update_model(self, model_id: int, data: dict) -> dict | None:
        fields = []
        values = []
        for key, val in data.items():
            if key != "id":
                fields.append(f"{key} = ?")
                values.append(val)
        if not fields:
            return await self.get_model(model_id)
        values.append(model_id)
        await self.db.execute(
            f"UPDATE models SET {', '.join(fields)} WHERE id = ?", tuple(values)
        )
        await self.db.commit()
        return await self.get_model(model_id)

    async def delete_model(self, model_id: int) -> bool:
        cursor = await self.db.execute("DELETE FROM models WHERE id = ?", (model_id,))
        await self.db.commit()
        return cursor.rowcount > 0

    # --- assumptions tables (DCF, DDM, RevBased, Comps) ---

    async def get_assumptions(self, model_id: int, model_type: str) -> dict | None:
        table = f"{model_type}_assumptions"
        return await self.db.fetchone(
            f"SELECT * FROM {table} WHERE model_id = ?", (model_id,)
        )

    async def upsert_assumptions(self, model_id: int, model_type: str, data: dict) -> dict:
        table = f"{model_type}_assumptions"
        existing = await self.get_assumptions(model_id, model_type)

        if existing:
            fields = []
            values = []
            for key, val in data.items():
                if key not in ("id", "model_id"):
                    fields.append(f"{key} = ?")
                    values.append(val)
            if fields:
                values.append(model_id)
                await self.db.execute(
                    f"UPDATE {table} SET {', '.join(fields)} WHERE model_id = ?",
                    tuple(values),
                )
                await self.db.commit()
        else:
            cols = ["model_id"] + [k for k in data if k not in ("id", "model_id")]
            placeholders = ", ".join(["?"] * len(cols))
            vals = [model_id] + [data[k] for k in cols[1:]]
            await self.db.execute(
                f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})",
                tuple(vals),
            )
            await self.db.commit()

        return await self.get_assumptions(model_id, model_type)

    # --- model_outputs table ---

    async def get_output(self, output_id: int) -> dict | None:
        return await self.db.fetchone("SELECT * FROM model_outputs WHERE id = ?", (output_id,))

    async def get_outputs_for_model(self, model_id: int) -> list[dict]:
        return await self.db.fetchall(
            "SELECT * FROM model_outputs WHERE model_id = ? ORDER BY run_number DESC",
            (model_id,),
        )

    async def create_output(self, data: dict) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        cursor = await self.db.execute(
            """INSERT INTO model_outputs
               (model_id, run_number, run_timestamp,
                intrinsic_value_per_share, enterprise_value, equity_value,
                terminal_value_perpetuity, terminal_value_exit_multiple,
                tv_pct_of_ev_perpetuity, tv_pct_of_ev_exit,
                waterfall_data_json, projection_table_json,
                scenarios_json, uncertainty_level, scenario_count,
                sensitivity_sliders_json, sensitivity_tornado_json,
                sensitivity_montecarlo_json, sensitivity_tables_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["model_id"],
                data["run_number"],
                now,
                data.get("intrinsic_value_per_share"),
                data.get("enterprise_value"),
                data.get("equity_value"),
                data.get("terminal_value_perpetuity"),
                data.get("terminal_value_exit_multiple"),
                data.get("tv_pct_of_ev_perpetuity"),
                data.get("tv_pct_of_ev_exit"),
                data.get("waterfall_data_json"),
                data.get("projection_table_json"),
                data.get("scenarios_json"),
                data.get("uncertainty_level"),
                data.get("scenario_count"),
                data.get("sensitivity_sliders_json"),
                data.get("sensitivity_tornado_json"),
                data.get("sensitivity_montecarlo_json"),
                data.get("sensitivity_tables_json"),
            ),
        )
        await self.db.commit()
        return await self.get_output(cursor.lastrowid)

    # --- model_versions table ---

    async def get_version(self, version_id: int) -> dict | None:
        return await self.db.fetchone("SELECT * FROM model_versions WHERE id = ?", (version_id,))

    async def get_versions_for_model(self, model_id: int) -> list[dict]:
        return await self.db.fetchall(
            "SELECT id, model_id, version_number, annotation, snapshot_size_bytes, created_at "
            "FROM model_versions WHERE model_id = ? ORDER BY version_number DESC",
            (model_id,),
        )

    async def create_version(self, data: dict) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        cursor = await self.db.execute(
            """INSERT INTO model_versions
               (model_id, version_number, snapshot_blob, annotation,
                snapshot_size_bytes, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                data["model_id"],
                data["version_number"],
                data["snapshot_blob"],
                data.get("annotation"),
                data.get("snapshot_size_bytes"),
                now,
            ),
        )
        await self.db.commit()
        return await self.get_version(cursor.lastrowid)
