"""
受害人维表服务 - CRUD + PostgreSQL 同步 + Excel导入
表: taosha.dim_taosha_victim_account
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import text

from utils.analyze_db_utils import AnalyzeDBConnector
from utils.logger import logger


class VictimAccountExistsError(Exception):
    """账号已存在，用于 create 时前置校验"""
    pass


class VictimEntryService:
    """受害人维表服务（MySQL CRUD + PG 同步）"""

    TABLE = "dim_taosha_victim_account"

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
        """分页查询，支持 account_no / account_name 模糊搜索"""
        offset = (page - 1) * page_size
        params: Dict[str, Any] = {"limit": page_size, "offset": offset}

        if search:
            params["search"] = f"%{search}%"
            where_clause = """
                WHERE account_no LIKE :search
                   OR account_name LIKE :search
            """
        else:
            where_clause = ""

        count_sql = text(f"SELECT COUNT(*) AS total FROM {self.TABLE}{where_clause}")
        rows_sql = text(f"""
            SELECT account_no, account_name
            FROM {self.TABLE}
            {where_clause}
            ORDER BY account_no ASC
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

    def get_by_account_no(self, account_no: str) -> Optional[Dict[str, Any]]:
        """根据 account_no 精确查单条"""
        import traceback as _tb
        sql = text(
            f"SELECT account_no, account_name "
            f"FROM {self.TABLE} WHERE account_no = :account_no"
        )
        try:
            row = self.db.execute(sql, {"account_no": account_no}).fetchone()
        except Exception as e:
            logger.error(
                f"[VictimEntry.get_by_account_no] 查询失败 account_no={account_no} "
                f"error={e}\n{_tb.format_exc()}"
            )
            raise
        if row:
            return self._row_to_tuple(row)
        return None

    def create(
        self,
        account_no: str,
        account_name: str,
    ) -> Dict[str, Any]:
        """
        新增一条，同步至 PG。

        Raises:
            VictimAccountExistsError: account_no 已存在时抛出（由路由层转 400）
        """
        import traceback as _tb

        logger.info(f"[VictimEntry.create] 开始新增 account_no={account_no}")

        # ── 前置重复检测 ──────────────────────────────────────────────
        dup_sql = text(f"SELECT 1 FROM {self.TABLE} WHERE account_no=:an LIMIT 1")
        try:
            exists = self.db.execute(dup_sql, {"an": account_no}).fetchone()
        except Exception as e:
            logger.error(
                f"[VictimEntry.create] 步骤①重复检测失败 account_no={account_no} "
                f"error={e}\n{_tb.format_exc()}"
            )
            raise
        if exists:
            raise VictimAccountExistsError(
                f"账号 '{account_no}' 已存在，请勿重复添加"
            )

        # ── 写入 MySQL ─────────────────────────────────────────────────
        ins_sql = text(f"""
            INSERT INTO {self.TABLE} (account_no, account_name)
            VALUES (:account_no, :account_name)
        """)
        try:
            self.db.execute(ins_sql, {
                "account_no": account_no,
                "account_name": account_name,
            })
            logger.info(f"[VictimEntry.create] 步骤②MySQL写入成功 account_no={account_no}")
        except Exception as e:
            logger.error(
                f"[VictimEntry.create] 步骤②MySQL写入失败 account_no={account_no} "
                f"error={e}\n{_tb.format_exc()}"
            )
            raise

        # ── 同步 PG（有记录的 upsert，正常不应失败）──────────────────────
        try:
            self._upsert_pg(account_no, account_name)
            logger.info(f"[VictimEntry.create] 步骤③PG同步完成 account_no={account_no}")
        except Exception as e:
            logger.error(
                f"[VictimEntry.create] 步骤③PG同步异常 account_no={account_no} "
                f"error={e}\n{_tb.format_exc()}"
            )

        # ── 回查 MySQL 确认写入成功 ────────────────────────────────────
        try:
            result = self.get_by_account_no(account_no)
            logger.info(f"[VictimEntry.create] 完成 account_no={account_no}")
            return result
        except Exception as e:
            logger.error(
                f"[VictimEntry.create] 步骤④回查失败 account_no={account_no} "
                f"error={e}\n{_tb.format_exc()}"
            )
            raise

    def update(
        self,
        old_account_no: str,
        account_no: str,
        account_name: str,
    ) -> bool:
        """
        更新一条，同步至 PG；如果 account_no 发生变化则删旧插新。

        Raises:
            VictimAccountExistsError: 目标 account_no 已存在（仅在 rename 场景可能出现）
        """
        import traceback as _tb

        if old_account_no == account_no:
            upd_sql = text(f"""
                UPDATE {self.TABLE}
                SET account_name=:account_name
                WHERE account_no=:account_no
            """)
            try:
                r = self.db.execute(upd_sql, {
                    "account_no": account_no,
                    "account_name": account_name,
                })
                ok = r.rowcount > 0
            except Exception as e:
                logger.error(
                    f"[VictimEntry.update] 更新失败 old_account_no={old_account_no} "
                    f"error={e}\n{_tb.format_exc()}"
                )
                raise
        else:
            # 检测 rename 后目标 key 是否已被占用
            dup_sql = text(f"SELECT 1 FROM {self.TABLE} WHERE account_no=:an LIMIT 1")
            try:
                exists = self.db.execute(dup_sql, {"an": account_no}).fetchone()
            except Exception as e:
                logger.error(
                    f"[VictimEntry.update] 重复检测失败 account_no={account_no} "
                    f"error={e}\n{_tb.format_exc()}"
                )
                raise
            if exists:
                raise VictimAccountExistsError(
                    f"目标账号 '{account_no}' 已存在，无法重命名"
                )

            del_sql = text(f"DELETE FROM {self.TABLE} WHERE account_no=:old")
            ins_sql = text(f"""
                INSERT INTO {self.TABLE} (account_no, account_name)
                VALUES (:account_no, :account_name)
            """)
            try:
                self.db.execute(del_sql, {"old": old_account_no})
                self.db.execute(ins_sql, {
                    "account_no": account_no,
                    "account_name": account_name,
                })
                ok = True
            except Exception as e:
                logger.error(
                    f"[VictimEntry.update] rename 失败 old_account_no={old_account_no} "
                    f"error={e}\n{_tb.format_exc()}"
                )
                raise

        # ── 同步 PG ──────────────────────────────────────────────────────
        try:
            self._upsert_pg(account_no, account_name)
        except Exception as e:
            logger.warning(
                f"[VictimEntry.update] PG同步失败 account_no={account_no} error={e}"
            )

        return ok

    def delete(self, account_no: str) -> bool:
        """删除 MySQL 记录，同步删除 PG。PG 删除失败记录 warning 但不阻止返回值。"""
        sql = text(f"DELETE FROM {self.TABLE} WHERE account_no=:account_no")
        try:
            r = self.db.execute(sql, {"account_no": account_no})
            ok = r.rowcount > 0
        except Exception as e:
            import traceback as _tb
            logger.error(
                f"[VictimEntry.delete] 删除失败 account_no={account_no} "
                f"error={e}\n{_tb.format_exc()}"
            )
            raise

        try:
            self._delete_from_pg(account_no)
        except Exception:
            pass  # 静默，保持删除操作的原子性

        return ok

    def batch_import_from_records(self, records: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        从记录列表批量导入（追加模式）。

        Args:
            records: [{"account_no": "...", "account_name": "..."}, ...]

        Returns:
            {"success_count": N, "skip_count": M, "errors": [...]}
        """
        """
        批量导入（追加模式）。
        对于已存在的账号，执行覆盖更新；对于新账号，执行插入。

        Args:
            records: [{"account_no": "...", "account_name": "..."}, ...]

        Returns:
            {"success_count": N, "skip_count": M, "errors": [...]}
        """
        import traceback as _tb

        success_count = 0
        skip_count = 0
        errors: List[str] = []

        for idx, record in enumerate(records):
            account_no = (record.get("account_no") or "").strip()
            account_name = (record.get("account_name") or "").strip()

            if not account_no:
                errors.append(f"第{idx + 1}行：账号不能为空，跳过")
                continue

            try:
                # 检查是否存在
                existing = self.get_by_account_no(account_no)

                if existing:
                    # 已存在，覆盖更新
                    self.update(existing["account_no"], account_no, account_name)
                else:
                    # 不存在，新增
                    self.create(account_no, account_name)

                success_count += 1
            except Exception as e:
                err_msg = f"第{idx + 1}行：账号'{account_no}'导入失败，错误：{str(e)}"
                logger.error(f"[VictimEntry.batch_import] {err_msg}\n{_tb.format_exc()}")
                errors.append(err_msg)

        logger.info(
            f"[VictimEntry.batch_import_from_records] 完成，成功:{success_count}，跳过:{skip_count}，失败:{len(errors)}"
        )

        return {
            "success_count": success_count,
            "skip_count": skip_count,
            "errors": errors[:100],  # 最多保留100条错误信息
        }

    def batch_import_from_file(self, file_content: bytes) -> Dict[str, Any]:
        """
        从 Excel 文件批量导入（追加模式）。

        Args:
            file_content: Excel 文件二进制内容

        Returns:
            {"success_count": N, "total_rows": M, "errors": [...], "skipped_rows": K}
        """
        import io as _io
        import pandas as _pd

        logger.info("[VictimEntry.batch_import_from_file] 开始解析 Excel 文件")

        try:
            df = _pd.read_excel(_io.BytesIO(file_content))
        except Exception as e:
            raise ValueError(f"无法解析 Excel 文件，请确保是有效的 .xlsx 或 .xls 文件：{str(e)}")

        # 处理 NaN 值
        df = df.fillna("")
        headers = [str(h).strip().lower() for h in df.columns]

        # 找账号列和户名列（支持多种表头名称）
        account_no_idx = None
        account_name_idx = None

        for idx, h in enumerate(headers):
            if account_no_idx is None and ("账号" in h or "account" in h or "卡号" in h):
                account_no_idx = idx
            elif account_name_idx is None and ("户名" in h or "姓名" in h or "name" in h or "account_name" in h):
                account_name_idx = idx

        if account_no_idx is None:
            raise ValueError("未找到'账号'列，请在 Excel 第一行添加包含'账号'或'卡号'的列名")

        # 构建记录列表
        records: List[Dict[str, str]] = []
        skipped_rows = 0

        for _, row in df.iterrows():
            account_no = str(row.iloc[account_no_idx]).strip()
            if not account_no:
                skipped_rows += 1
                continue

            account_name = ""
            if account_name_idx is not None:
                account_name = str(row.iloc[account_name_idx]).strip()

            records.append({
                "account_no": account_no,
                "account_name": account_name,
            })

        total_rows = len(records)
        logger.info(f"[VictimEntry.batch_import_from_file] 解析完成，共 {total_rows} 条有效数据，跳过 {skipped_rows} 空行")

        if total_rows == 0:
            raise ValueError("文件中没有可导入的有效数据（账号列为空）")

        # 执行批量导入
        result = self.batch_import_from_records(records)

        return {
            "success_count": result["success_count"],
            "total_rows": total_rows,
            "skipped_rows": skipped_rows + result["skip_count"],
            "errors": result["errors"],
        }

    # ------------------------------------------------------------------
    # PostgreSQL 同步（均采用 upsert-on-conflict，防并发幂等）
    # ------------------------------------------------------------------

    def _upsert_pg(
        self,
        account_no: str,
        account_name: str,
    ):
        """
        Upsert 至 PostgreSQL。

        依赖 PG 表上有 UNIQUE(account_no) 约束；若不存在，ON CONFLICT
        会报 constraint 错误，本方法将其提升为 warning 并记录详细堆栈。
        """
        import traceback as _tb
        logger.info(f"[VictimEntry._upsert_pg] >>> 进入UPSERT account_no={account_no}")
        try:
            sql = text("""
                INSERT INTO dim_taosha_victim_account (account_no, account_name)
                VALUES (:account_no, :account_name)
                ON CONFLICT (account_no) DO UPDATE SET
                    account_name = EXCLUDED.account_name
            """)
            AnalyzeDBConnector.execute_sql(sql, {
                "account_no": account_no,
                "account_name": account_name,
            }, fetch_df=False)
            logger.info(f"[VictimEntry._upsert_pg] <<< UPSERT成功 account_no={account_no}")
        except Exception as e:
            logger.warning(
                f"[VictimEntry._upsert_pg] <<< UPSERT失败 account_no={account_no} "
                f"error={e}\n{_tb.format_exc()}"
            )

    def _delete_from_pg(self, account_no: str):
        """删除 PG 中对应记录，任何异常均打印 warning 但不抛出让调用方感知。"""
        try:
            pg_del_sql = text(
                "DELETE FROM dim_taosha_victim_account WHERE account_no=:account_no"
            )
            AnalyzeDBConnector.execute_sql(
                pg_del_sql, {"account_no": account_no}, fetch_df=False
            )
            logger.info(f"[VictimEntry] 删除PG数据成功: {account_no}")
        except Exception as e:
            logger.warning(
                f"[VictimEntry] 删除PG数据失败（账号={account_no}，"
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
            "account_no": row[0],
            "account_name": row[1],
        }


def get_victim_entry_service(db: Session) -> VictimEntryService:
    return VictimEntryService(db)


# Re-export 领域异常，供路由层 import
__all__ = ["get_victim_entry_service", "VictimEntryService", "VictimAccountExistsError"]