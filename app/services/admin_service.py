"""
OJ System - 管理员备份与恢复业务逻辑
"""
import os
import json
import shutil
from datetime import datetime, timezone

from fastapi import HTTPException

import app.repositories.manager as mgr
from app.services.submission_service import _write_audit_log
from app.models.enums import AuditAction

# 需要备份的数据文件列表
DATA_FILES = [
    "users.json",
    "problems.json",
    "submissions.json",
    "judge_logs.json",
    "audit_logs.json",
    "backups.json",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fmt_now() -> str:
    """返回用于文件名的紧凑时间戳"""
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def create_backup(operator_id: str) -> dict:
    """
    创建备份。
    1. 创建以时间戳命名的备份目录
    2. 复制所有数据文件到备份目录
    3. 生成 manifest.json
    4. 记录审计日志
    """
    backup_id = f"backup_{_fmt_now()}"
    backup_dir = os.path.join(mgr.BACKUP_DIR, backup_id)
    os.makedirs(backup_dir, exist_ok=True)

    file_list = []
    for filename in DATA_FILES:
        src = os.path.join(mgr.DATA_DIR, filename)
        dst = os.path.join(backup_dir, filename)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            file_list.append(filename)

    # 创建 manifest
    manifest = {
        "backup_id": backup_id,
        "created_at": _now_iso(),
        "storage_type": "json",
        "files": file_list,
    }
    with open(os.path.join(backup_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # 保存备份记录
    backups = mgr.load_json("backups.json")
    backups[backup_id] = manifest
    mgr.save_json("backups.json", backups)

    # 审计日志
    _write_audit_log(operator_id, AuditAction.CREATE_BACKUP.value, "backup", backup_id)

    return {"backup_id": backup_id, "created_at": manifest["created_at"]}


def list_backups() -> list[dict]:
    """列出所有备份"""
    backups = mgr.load_json("backups.json")
    result = list(backups.values())
    result.sort(key=lambda b: b.get("created_at", ""), reverse=True)
    return result


def restore_backup(backup_id: str, operator_id: str) -> None:
    """
    从备份恢复数据。
    1. 验证备份存在且 manifest 有效
    2. 将当前数据临时备份到安全位置
    3. 用备份文件覆盖当前数据
    4. 如果失败，从安全副本恢复
    """
    backup_dir = os.path.join(mgr.BACKUP_DIR, backup_id)
    manifest_path = os.path.join(backup_dir, "manifest.json")

    if not os.path.exists(manifest_path):
        raise HTTPException(status_code=404, detail="backup not found")

    # 验证 manifest
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="backup manifest is corrupted")

    required_files = manifest.get("files", [])
    for fname in required_files:
        if not os.path.exists(os.path.join(backup_dir, fname)):
            raise HTTPException(status_code=400, detail=f"backup file '{fname}' is missing")

    # 创建安全副本
    safety_dir = os.path.join(mgr.BACKUP_DIR, f"_safety_{_fmt_now()}")
    os.makedirs(safety_dir, exist_ok=True)
    try:
        for fname in required_files:
            src = os.path.join(mgr.DATA_DIR, fname)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(safety_dir, fname))
    except Exception as e:
        # 安全副本创建失败，放弃恢复
        raise HTTPException(status_code=500, detail=f"failed to create safety copy: {e}")

    # 用备份覆盖当前数据
    try:
        for fname in required_files:
            src = os.path.join(backup_dir, fname)
            dst = os.path.join(mgr.DATA_DIR, fname)
            shutil.copy2(src, dst)
    except Exception as e:
        # 恢复失败 → 从安全副本回滚
        _rollback_from_safety(safety_dir, required_files)
        raise HTTPException(status_code=500, detail=f"restore failed, data rolled back: {e}")

    # 清理安全副本
    try:
        shutil.rmtree(safety_dir, ignore_errors=True)
    except Exception:
        pass

    # 审计日志
    _write_audit_log(operator_id, AuditAction.RESTORE_BACKUP.value, "backup", backup_id)


def _rollback_from_safety(safety_dir: str, files: list[str]):
    """恢复失败时从安全副本回滚数据"""
    for fname in files:
        src = os.path.join(safety_dir, fname)
        dst = os.path.join(mgr.DATA_DIR, fname)
        if os.path.exists(src):
            try:
                shutil.copy2(src, dst)
            except Exception:
                pass
