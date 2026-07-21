"""
Upload utilities — filename sanitization and file size validation.

Functions:
    safe_filename(filename) -> str
        Strips path components, null bytes, and special characters.
        Raises ValueError for invalid filenames.

    get_max_upload_bytes() -> int
        Returns MAX_UPLOAD_BYTES env var (default: 25MB).

    get_upload_file_size(file) -> int
        Returns the size of an UploadFile by seeking to end.

Env vars used:
    MAX_UPLOAD_BYTES - Max upload size in bytes (default: 26214400 = 25MB)
"""

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
