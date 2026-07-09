from __future__ import annotations

import os
import re
from fastapi import UploadFile

DEFAULT_MAX_UPLOAD_BYTES = 25 * 1024 * 1024


def safe_filename(filename: str) -> str:
    base_name = os.path.basename((filename or "").replace("\\", "/")).strip()
    base_name = base_name.replace("\x00", "")
    base_name = re.sub(r"[^A-Za-z0-9._-]+", "_", base_name).strip("._")

    if not base_name or base_name in {".", ".."}:
        raise ValueError("Invalid filename")

    return base_name


def get_max_upload_bytes() -> int:
    return int(os.getenv("MAX_UPLOAD_BYTES", str(DEFAULT_MAX_UPLOAD_BYTES)))


def get_upload_file_size(file: UploadFile) -> int:
    current_position = file.file.tell()
    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(current_position)
    return size