"""
省市卡BIN维表服务 - CRUD + PostgreSQL 同步
表: taosha.dim_all_province_card_bin
"""

from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from utils.analyze_db_utils import AnalyzeDBConnector
from utils.logger import logger


class ProvinceCardBinService:
    """省市卡BIN维表服务（MySQL CRUD + PG 同步）"""

    TABLE = "dim_all_province_card_bin"

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # MySQL 读写
    # ------------------------------------------------------------------

    def list_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """分页查询，支持 card_bin / bank_name / province / city 模糊搜索"""
        offset = (page - 1) * page_size

        if search:
            like = f"%{search}%"
            where_clause = """
                WHERE card_bin LIKE :search
                   OR bank_name LIKE :search
                   OR province LIKE :search
                   OR city LIKE :search
            """
        else:
            where_clause = ""

        count_sql = text(f"SELECT COUNT(*) AS total FROM {self.TABLE} {where_clause}")
        rows_sql = text(f"""
            SELECT card_bin, bank_name, province, city, updated_at
            FROM {self.TABLE}
            {where_clause}
            ORDER BY updated_at DESC NULLS LAST
            LIMIT :limit OFFSET :offset
        """)
        params = {"search": like} if search else {}

        with self.db.connection() as conn:
            total_row = conn.execute(count_sql, params).fetchone()
            total = total_row[0] if total_row else 0

            rows = conn.execute(rows_sql, {**params, "limit": page_size, "offset": offset}).fetchall()

        items = [self._row_to_dict(r) for r in rows]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    def get_by_card_bin(self, card_bin: str) -> Optional[Dict[str, Any]]:
        """根据 card_bin 精确查单条"""
        sql = text(f"SELECT card_bin, bank_name, province, city, updated_at FROM {self.TABLE} WHERE card_bin = :card_bin")
        with self.db.connection() as conn:
            row = conn.execute(sql, {"card_bin": card_bin}).fetchone()
        if row:
            return self._row_to_dict(row)
        return None

    def create(
        self,
        card_bin: str,
        bank_name: str,
        province: str,
        city: str,
    ) -> Dict[str, Any]:
        """新增一条，同步至 PG"""
        sql = text(f"""
            INSERT INTO {self.TABLE} (card_bin, bank_name, province, city)
            VALUES (:card_bin, :bank_name, :province, :city)
        """)
        with self.db.connection() as conn:
            conn.execute(sql, {
                "card_bin": card_bin,
                "bank_name": bank_name,
                "province": province,
                "city": city,
            })
            conn.commit()

        self._sync_to_pg(card_bin, bank_name, province, city)
        return self.get_by_card_bin(card_bin)

    def update(
        self,
        old_card_bin: str,
        card_bin: str,
        bank_name: str,
        province: str,
        city: str,
    ) -> bool:
        """更新一条，同步至 PG；如果 card_bin 变了，先删旧记录再插新记录"""
        if old_card_bin == card_bin:
            sql = text(f"""
                UPDATE {self.TABLE}
                SET bank_name=:bank_name, province=:province, city=:city, updated_at=NOW()
                WHERE card_bin=:card_bin
            """)
            with self.db.connection() as conn:
                r = conn.execute(sql, {
                    "card_bin": card_bin,
                    "bank_name": bank_name,
                    "province": province,
                    "city": city,
                })
                conn.commit()
            ok = r.rowcount > 0
        else:
            # card_bin 变化：删旧的，插新的
            del_sql = text(f"DELETE FROM {self.TABLE} WHERE card_bin=:old")
            ins_sql = text(f"""
                INSERT INTO {self.TABLE} (card_bin, bank_name, province, city)
                VALUES (:card_bin, :bank_name, :province, :city)
            """)
            with self.db.connection() as conn:
                conn.execute(del_sql, {"old": old_card_bin})
                conn.execute(ins_sql, {
                    "card_bin": card_bin,
                    "bank_name": bank_name,
                    "province": province,
                    "city": city,
                })
                conn.commit()
            ok = True

        self._sync_to_pg(card_bin, bank_name, province, city)
        return ok

    def delete(self, card_bin: str) -> bool:
        """删除一条，同时删 PG"""
        sql = text(f"DELETE FROM {self.TABLE} WHERE card_bin=:card_bin")
        with self.db.connection() as conn:
            r = conn.execute(sql, {"card_bin": card_bin})
            conn.commit()
        ok = r.rowcount > 0

        try:
            pg_del_sql = text("DELETE FROM dim_all_province_card_bin WHERE card_bin=:card_bin")
            AnalyzeDBConnector.execute_sql(pg_del_sql, {"card_bin": card_bin})
        except Exception as e:
            logger.warning(f"[ProvinceCardBin] 删除PG数据失败（不影响本地）: {e}")

        return ok

    # ------------------------------------------------------------------
    # PostgreSQL 同步
    # ------------------------------------------------------------------

    def _sync_to_pg(
        self,
        card_bin: str,
        bank_name: str,
        province: str,
        city: str,
    ):
        """Upsert 至 PostgreSQL（静默失败，不阻塞主流程）"""
        try:
            sql = text("""
                INSERT INTO dim_all_province_card_bin (card_bin, bank_name, province, city)
                VALUES (:card_bin, :bank_name, :province, :city)
                ON CONFLICT (card_bin) DO UPDATE SET
                    bank_name = EXCLUDED.bank_name,
                    province = EXCLUDED.province,
                    city = EXCLUDED.city
            """)
            AnalyzeDBConnector.execute_sql(sql, {
                "card_bin": card_bin,
                "bank_name": bank_name,
                "province": province,
                "city": city,
            })
            logger.info(f"[ProvinceCardBin] 同步至PG成功: {card_bin}")
        except Exception as e:
            logger.warning(f"[ProvinceCardBin] 同步至PG失败（已记录，继续）：{e}")

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        return {
            "card_bin": row[0],
            "bank_name": row[1],
            "province": row[2],
            "city": row[3],
            "updated_at": row[4].isoformat() if row[4] else None,
        }


def get_province_card_bin_service(db: Session) -> ProvinceCardBinService:
    return ProvinceCardBinService(db)