"""
省市卡BIN维表服务 - CRUD + PostgreSQL 同步
表: taosha.dim_all_province_card_bin
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from utils.analyze_db_utils import AnalyzeDBConnector
from utils.logger import logger


class ProvinceCardBinExistsError(Exception):
    """卡BIN已存在，用于 create 时前置校验"""
    pass


class ProvinceCardBinService:
    """省市卡BIN维表服务（MySQL CRUD + PG 同步）"""

    TABLE = "dim_all_province_card_bin"

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # MySQL 读写（直接基于 Session 操作，不单独获取连接，
    # FastAPI 依赖注入的 db 会话已在 get_db 中完成 commit/rollback）
    # ------------------------------------------------------------------

    def list_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """分页查询，支持 card_bin / bank_name / province / city 模糊搜索"""
        offset = (page - 1) * page_size
        params: Dict[str, Any] = {"limit": page_size, "offset": offset}

        if search:
            params["search"] = f"%{search}%"
            where_clause = """
                WHERE card_bin LIKE :search
                   OR bank_name LIKE :search
                   OR province LIKE :search
                   OR city LIKE :search
            """
        else:
            where_clause = ""

        count_sql = text(f"SELECT COUNT(*) AS total FROM {self.TABLE}{where_clause}")
        rows_sql = text(f"""
            SELECT card_bin, bank_name, province, city
            FROM {self.TABLE}
            {where_clause}
            ORDER BY card_bin ASC
            LIMIT :limit OFFSET :offset
        """)

        total = self.db.execute(count_sql, params).scalar() or 0
        rows = self.db.execute(rows_sql, params).fetchall()

        return {
            "items": [self._row_to_tuple(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_by_card_bin(self, card_bin: str) -> Optional[Dict[str, Any]]:
        """根据 card_bin 精确查单条"""
        import traceback as _tb
        sql = text(
            f"SELECT card_bin, bank_name, province, city "
            f"FROM {self.TABLE} WHERE card_bin = :card_bin"
        )
        try:
            row = self.db.execute(sql, {"card_bin": card_bin}).fetchone()
        except Exception as e:
            logger.error(
                f"[ProvinceCardBin.get_by_card_bin] 查询失败 card_bin={card_bin} "
                f"error={e}\n{_tb.format_exc()}"
            )
            raise
        if row:
            return self._row_to_tuple(row)
        return None

    def create(
        self,
        card_bin: str,
        bank_name: str,
        province: str,
        city: str,
    ) -> Dict[str, Any]:
        """
        新增一条，同步至 PG。

        Raises:
            ProvinceCardBinExistsError: card_bin 已存在时抛出（由路由层转 400）
        """
        import traceback as _tb

        logger.info(f"[ProvinceCardBin.create] 开始新增 card_bin={card_bin}")

        # ── 前置重复检测 ──────────────────────────────────────────────
        dup_sql = text(f"SELECT 1 FROM {self.TABLE} WHERE card_bin=:cb LIMIT 1")
        try:
            exists = self.db.execute(dup_sql, {"cb": card_bin}).fetchone()
        except Exception as e:
            logger.error(
                f"[ProvinceCardBin.create] 步骤①重复检测失败 card_bin={card_bin} "
                f"error={e}\n{_tb.format_exc()}"
            )
            raise
        if exists:
            raise ProvinceCardBinExistsError(
                f"卡BIN '{card_bin}' 已存在，请勿重复添加"
            )

        # ── 写入 MySQL ─────────────────────────────────────────────────
        ins_sql = text(f"""
            INSERT INTO {self.TABLE} (card_bin, bank_name, province, city)
            VALUES (:card_bin, :bank_name, :province, :city)
        """)
        try:
            self.db.execute(ins_sql, {
                "card_bin": card_bin,
                "bank_name": bank_name,
                "province": province,
                "city": city,
            })
            logger.info(f"[ProvinceCardBin.create] 步骤②MySQL写入成功 card_bin={card_bin}")
        except Exception as e:
            logger.error(
                f"[ProvinceCardBin.create] 步骤②MySQL写入失败 card_bin={card_bin} "
                f"error={e}\n{_tb.format_exc()}"
            )
            raise

        # ── 同步 PG（有记录的 upsert，正常不应失败）──────────────────────
        try:
            self._upsert_pg(card_bin, bank_name, province, city)
            logger.info(f"[ProvinceCardBin.create] 步骤③PG同步完成 card_bin={card_bin}")
        except Exception as e:
            logger.error(
                f"[ProvinceCardBin.create] 步骤③PG同步异常 card_bin={card_bin} "
                f"error={e}\n{_tb.format_exc()}"
            )

        # ── 回查 MySQL 确认写入成功 ────────────────────────────────────
        try:
            result = self.get_by_card_bin(card_bin)
            logger.info(f"[ProvinceCardBin.create] 完成 card_bin={card_bin}")
            return result
        except Exception as e:
            logger.error(
                f"[ProvinceCardBin.create] 步骤④回查失败 card_bin={card_bin} "
                f"error={e}\n{_tb.format_exc()}"
            )
            raise

    def update(
        self,
        old_card_bin: str,
        card_bin: str,
        bank_name: str,
        province: str,
        city: str,
    ) -> bool:
        """
        更新一条，同步至 PG；如果 card_bin 发生变化则删旧插新。

        Raises:
            ProvinceCardBinExistsError: 目标 card_bin 已存在（仅在 rename 场景可能出现）
        """
        import traceback as _tb

        if old_card_bin == card_bin:
            upd_sql = text(f"""
                UPDATE {self.TABLE}
                SET bank_name=:bank_name, province=:province, city=:city
                WHERE card_bin=:card_bin
            """)
            try:
                r = self.db.execute(upd_sql, {
                    "card_bin": card_bin,
                    "bank_name": bank_name,
                    "province": province,
                    "city": city,
                })
                # Connection.execute 返回 RowCount，需要通过 connection 来获取
                # 用 session.execute 配合 rowcount 需要换一种方式：用 scalar_subquery 或直接查
                ok = r.rowcount > 0
            except Exception as e:
                logger.error(
                    f"[ProvinceCardBin.update] 更新失败 old_card_bin={old_card_bin} "
                    f"error={e}\n{_tb.format_exc()}"
                )
                raise
        else:
            # 检测 rename 后目标 key 是否已被占用
            dup_sql = text(f"SELECT 1 FROM {self.TABLE} WHERE card_bin=:cb LIMIT 1")
            try:
                exists = self.db.execute(dup_sql, {"cb": card_bin}).fetchone()
            except Exception as e:
                logger.error(
                    f"[ProvinceCardBin.update] 重复检测失败 card_bin={card_bin} "
                    f"error={e}\n{_tb.format_exc()}"
                )
                raise
            if exists:
                raise ProvinceCardBinExistsError(
                    f"目标卡BIN '{card_bin}' 已存在，无法重命名"
                )

            del_sql = text(f"DELETE FROM {self.TABLE} WHERE card_bin=:old")
            ins_sql = text(f"""
                INSERT INTO {self.TABLE} (card_bin, bank_name, province, city)
                VALUES (:card_bin, :bank_name, :province, :city)
            """)
            try:
                self.db.execute(del_sql, {"old": old_card_bin})
                self.db.execute(ins_sql, {
                    "card_bin": card_bin,
                    "bank_name": bank_name,
                    "province": province,
                    "city": city,
                })
                ok = True
            except Exception as e:
                logger.error(
                    f"[ProvinceCardBin.update] rename 失败 old_card_bin={old_card_bin} "
                    f"error={e}\n{_tb.format_exc()}"
                )
                raise

        # ── 同步 PG ──────────────────────────────────────────────────────
        try:
            self._upsert_pg(card_bin, bank_name, province, city)
        except Exception as e:
            logger.warning(
                f"[ProvinceCardBin.update] PG同步失败 card_bin={card_bin} error={e}"
            )

        return ok

    def delete(self, card_bin: str) -> bool:
        """删除 MySQL 记录，同步删除 PG。PG 删除失败记录 warning 但不阻止返回值。"""
        sql = text(f"DELETE FROM {self.TABLE} WHERE card_bin=:card_bin")
        try:
            r = self.db.execute(sql, {"card_bin": card_bin})
            ok = r.rowcount > 0
        except Exception as e:
            import traceback as _tb
            logger.error(
                f"[ProvinceCardBin.delete] 删除失败 card_bin={card_bin} "
                f"error={e}\n{_tb.format_exc()}"
            )
            raise

        try:
            self._delete_from_pg(card_bin)
        except Exception:
            pass  # 静默，保持删除操作的原子性

        return ok

    # ------------------------------------------------------------------
    # PostgreSQL 同步（均采用 upsert-on-conflict，防并发幂等）
    # ------------------------------------------------------------------

    def _upsert_pg(
        self,
        card_bin: str,
        bank_name: str,
        province: str,
        city: str,
    ):
        """
        Upsert 至 PostgreSQL。

        已知限制：
        - 依赖 PG 表上有 UNIQUE(card_bin) 约束；若不存在，ON CONFLICT
          会报 syntax-error / constraint 错误，本方法将其提升为 warning
          并记录 exc_info 以便排查，其余 IO 错误同样记录详细堆栈。
        """
        import traceback as _tb
        logger.info(f"[ProvinceCardBin._upsert_pg] >>> 进入UPSERT card_bin={card_bin}")
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
            }, fetch_df=False)
            logger.info(f"[ProvinceCardBin._upsert_pg] <<< UPSERT成功 card_bin={card_bin}")
        except Exception as e:
            logger.warning(
                f"[ProvinceCardBin._upsert_pg] <<< UPSERT失败 card_bin={card_bin} "
                f"error={e}\n{_tb.format_exc()}"
            )

    def _delete_from_pg(self, card_bin: str):
        """删除 PG 中对应记录，任何异常均打印 warning 但不抛出让调用方感知。"""
        try:
            pg_del_sql = text(
                "DELETE FROM dim_all_province_card_bin WHERE card_bin=:card_bin"
            )
            AnalyzeDBConnector.execute_sql(
                pg_del_sql, {"card_bin": card_bin}, fetch_df=False
            )
            logger.info(f"[ProvinceCardBin] 删除PG数据成功: {card_bin}")
        except Exception as e:
            logger.warning(
                f"[ProvinceCardBin] 删除PG数据失败（卡BIN={card_bin}，"
                f"不影响本地删除成功）: {e}",
                exc_info=True,
            )

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_tuple(row) -> Dict[str, Any]:
        # 使用索引取值（已知 SELECT 顺序固定），不加列名避免 Row 对象兼容问题
        return {
            "card_bin": row[0],
            "bank_name": row[1],
            "province": row[2],
            "city": row[3],
        }


def get_province_card_bin_service(db: Session) -> ProvinceCardBinService:
    return ProvinceCardBinService(db)


# Re-export 领域异常，供路由层 import
__all__ = ["get_province_card_bin_service", "ProvinceCardBinExistsError"]