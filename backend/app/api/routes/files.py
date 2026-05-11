"""
文件上传路由

提供附件上传、查询、清理接口。
上传的文件保存在 wence_data/project/uploads/ 目录下，以 UUID 命名防止冲突。
"""

import base64
import mimetypes
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.config import get_upload_dir, get_wence_project_dir

router = APIRouter()

# 上传目录
UPLOAD_DIR = get_upload_dir()

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".pdf",
    ".docx",
    ".txt",
    ".md",
    ".csv",
    ".yml",
    ".yaml",
    ".ymal",  # 兼容历史/误写扩展名
}

# 图片 MIME 类型
IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/jpg"}

# 单文件最大 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024

# ============== 响应模型 ==============


class UploadedFileInfo(BaseModel):
    """单个上传文件的信息"""

    file_id: str
    filename: str
    size: int
    content_type: str
    is_image: bool
    project_path: str
    absolute_path: str


class UploadResponse(BaseModel):
    """上传响应"""

    success: bool
    files: list[UploadedFileInfo] = []
    error: str | None = None


# ============== 工具函数 ==============


def _is_allowed_extension(filename: str) -> bool:
    """检查文件扩展名是否在允许列表中"""
    suffix = Path(filename).suffix.lower()
    return suffix in ALLOWED_EXTENSIONS


def _get_content_type(filename: str) -> str:
    """获取文件 MIME 类型"""
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


def get_file_path(file_id: str) -> Path | None:
    """根据 file_id 获取文件路径（安全校验）"""
    # file_id 格式: uuid_originalname
    file_path = UPLOAD_DIR / file_id
    if file_path.exists() and file_path.is_file() and file_path.resolve().parent == UPLOAD_DIR.resolve():
        return file_path
    return None


def get_file_project_path(file_id: str) -> str | None:
    """根据 file_id 获取 project 根目录下的相对路径（如 uploads/xxx）。"""
    file_path = get_file_path(file_id)
    if not file_path:
        return None
    project_root = get_wence_project_dir().resolve()
    try:
        return file_path.resolve().relative_to(project_root).as_posix()
    except Exception:
        return None


def read_file_as_base64(file_id: str) -> str | None:
    """读取文件并返回 base64 编码"""
    file_path = get_file_path(file_id)
    if not file_path:
        return None
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ============== 路由 ==============


@router.post("/upload", response_model=UploadResponse)
async def upload_files(files: list[UploadFile] = File(...)):
    """
    上传一个或多个文件

    支持格式: png, jpg, jpeg, pdf, docx, txt, md, csv, yml, yaml, ymal
    单文件最大 50MB
    返回每个文件在 project 下的路径，供 agent 后续通过 read_file 工具读取
    """
    results: list[UploadedFileInfo] = []

    for upload_file in files:
        filename = upload_file.filename or "unknown"

        # 校验扩展名
        if not _is_allowed_extension(filename):
            continue

        # 读取文件内容
        content = await upload_file.read()

        # 校验大小
        if len(content) > MAX_FILE_SIZE:
            continue

        # 生成唯一文件名
        file_id = f"{uuid.uuid4().hex}_{filename}"
        save_path = UPLOAD_DIR / file_id
        save_path.write_bytes(content)

        content_type = _get_content_type(filename)
        is_image = content_type in IMAGE_MIME_TYPES
        project_path = get_file_project_path(file_id) or f"uploads/{file_id}"

        results.append(
            UploadedFileInfo(
                file_id=file_id,
                filename=filename,
                size=len(content),
                content_type=content_type,
                is_image=is_image,
                project_path=project_path,
                absolute_path=str(save_path.resolve()),
            )
        )

    return UploadResponse(success=True, files=results)


@router.delete("/upload/{file_id}")
async def delete_uploaded_file(file_id: str):
    """删除已上传的文件"""
    file_path = get_file_path(file_id)
    if file_path:
        file_path.unlink(missing_ok=True)
        return {"success": True}
    return {"success": False, "error": "文件不存在"}


@router.get("/file")
async def get_uploaded_file(path: str = Query(..., description="Project-relative file path, e.g. uploads/xxx.png")):
    """读取 project 下的文件（用于 Office 插件拉取图片）。"""
    raw = path.strip().lstrip("/")
    if not raw:
        raise HTTPException(status_code=400, detail="path 不能为空")

    # 仅允许 uploads/temp 目录下的文件
    if not (raw.startswith("uploads/") or raw.startswith("temp/")):
        raise HTTPException(status_code=403, detail="不允许访问该路径")

    project_root = get_wence_project_dir().resolve()
    target = (project_root / raw).resolve()
    try:
        target.relative_to(project_root)
    except Exception:
        raise HTTPException(status_code=403, detail="非法路径")

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")

    mime, _ = mimetypes.guess_type(target.name)
    return FileResponse(path=target, media_type=mime or "application/octet-stream")
