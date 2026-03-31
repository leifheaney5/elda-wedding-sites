from __future__ import annotations

from dataclasses import dataclass

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app.models.contact import ContactAttachment

MAX_ATTACHMENT_BYTES = 8 * 1024 * 1024  # 8MB per file
ALLOWED_ATTACHMENT_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".doc",
    ".docx",
}
ALLOWED_ATTACHMENT_MIME_PREFIXES = (
    "image/",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
)


@dataclass
class UploadResult:
    attachment: ContactAttachment | None
    filename: str
    error: str | None = None


def is_attachment_allowed(filename: str, mime_type: str | None) -> bool:
    lower = (filename or "").lower()
    has_ext = any(lower.endswith(ext) for ext in ALLOWED_ATTACHMENT_EXTENSIONS)
    if not has_ext:
        return False
    if not mime_type:
        return True
    return any(mime_type.startswith(prefix) for prefix in ALLOWED_ATTACHMENT_MIME_PREFIXES)


def build_contact_attachment(
    file_obj: FileStorage,
    submission_id: int,
    uploaded_by: str,
) -> UploadResult:
    safe_name = secure_filename(file_obj.filename or "")
    mime_type = (file_obj.mimetype or "").strip()
    if not safe_name:
        return UploadResult(None, "", "empty filename")
    if not is_attachment_allowed(safe_name, mime_type):
        return UploadResult(None, safe_name, "type")

    data = file_obj.read()
    if len(data) > MAX_ATTACHMENT_BYTES:
        return UploadResult(None, safe_name, "size")

    attachment = ContactAttachment(
        submission_id=submission_id,
        filename=safe_name,
        mime_type=mime_type or None,
        data=data,
        size_bytes=len(data),
        uploaded_by=uploaded_by,
    )
    return UploadResult(attachment=attachment, filename=safe_name, error=None)

