"""Skills management API."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.services.agent.skills import delete_skill, discover_skills, install_skill_zip, set_skill_enabled

router = APIRouter()


class SkillEnableRequest(BaseModel):
    """Enable/disable payload for a skill."""

    enabled: bool


@router.get("/skills")
async def list_skills():
    """List downloaded skills discovered under wence_data/skills."""
    return {"skills": discover_skills(include_disabled=True)}


@router.post("/skills/upload")
async def upload_skill_package(file: UploadFile = File(...)):
    """Upload zip package and install it into wence_data/skills."""
    filename = (file.filename or "").strip()
    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="仅支持上传 .zip 压缩包")

    suffix = Path(filename).suffix or ".zip"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="wence_skill_upload_") as temp_file:
        temp_path = Path(temp_file.name)
        content = await file.read()
        temp_file.write(content)

    try:
        installed = install_skill_zip(temp_path, original_filename=filename)
        return {
            "success": True,
            "message": "Skill 上传并安装成功",
            "skill": installed,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"安装 skill 失败: {e}")
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass


@router.put("/skills/{folder}/enabled")
async def update_skill_enabled(folder: str, payload: SkillEnableRequest):
    """Set skill enabled state."""
    available_folders = {str(item.get("folder", "")) for item in discover_skills(include_disabled=True)}
    if folder not in available_folders:
        raise HTTPException(status_code=404, detail=f"Skill 不存在: {folder}")

    try:
        set_skill_enabled(folder, payload.enabled)
        return {"success": True, "folder": folder, "enabled": payload.enabled}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新 skill 状态失败: {e}")


@router.delete("/skills/{folder}")
async def remove_skill(folder: str):
    """Delete a skill from local skills folder."""
    try:
        delete_skill(folder)
        return {"success": True, "folder": folder}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Skill 不存在: {folder}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除 skill 失败: {e}")
