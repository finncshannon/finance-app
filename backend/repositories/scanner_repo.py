"""Repository for the scanner_presets table (user_data.db).

See phase0b_database_schema.md — Table #14.
"""

from datetime import datetime, timezone

from db.connection import DatabaseConnection


class ScannerRepo:

    def __init__(self, db: DatabaseConnection):
        self.db = db

    async def get_preset(self, preset_id: int) -> dict | None:
        return await self.db.fetchone("SELECT * FROM scanner_presets WHERE id = ?", (preset_id,))

    async def get_all_presets(self) -> list[dict]:
        return await self.db.fetchall("SELECT * FROM scanner_presets ORDER BY name")

    async def create_preset(self, data: dict) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        cursor = await self.db.execute(
            """INSERT INTO scanner_presets
               (name, query_text, filters_json, sector_filter, universe,
                form_types_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                data["name"],
                data.get("query_text"),
                data.get("filters_json"),
                data.get("sector_filter", "All"),
                data.get("universe", "sp500"),
                data.get("form_types_json", '["10-K"]'),
                now,
            ),
        )
        await self.db.commit()
        return await self.get_preset(cursor.lastrowid)

    async def update_preset(self, preset_id: int, data: dict) -> dict | None:
        now = datetime.now(timezone.utc).isoformat()
        fields = ["updated_at = ?"]
        values = [now]
        for key, val in data.items():
            if key not in ("id", "created_at"):
                fields.append(f"{key} = ?")
                values.append(val)
        values.append(preset_id)
        await self.db.execute(
            f"UPDATE scanner_presets SET {', '.join(fields)} WHERE id = ?",
            tuple(values),
        )
        await self.db.commit()
        return await self.get_preset(preset_id)

    async def delete_preset(self, preset_id: int) -> bool:
        cursor = await self.db.execute(
            "DELETE FROM scanner_presets WHERE id = ?", (preset_id,)
        )
        await self.db.commit()
        return cursor.rowcount > 0
