import os
import shutil
import uuid
import hashlib
import mimetypes
from pathlib import Path
from typing import List

from models.entities import Attachment
from database.repositories.attachment_repository import AttachmentRepository

class AttachmentService:
    def __init__(self):
        self.repository = AttachmentRepository()
        from config import ATTACHMENTS_STORAGE_DIR
        self.base_dir = ATTACHMENTS_STORAGE_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_attachments_for_entity(self, entity_type: str, entity_id: int) -> List[Attachment]:
        return self.repository.get_by_entity(entity_type, entity_id)

    def add_attachment(self, source_path: str, entity_type: str, entity_id: int) -> Attachment:
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        file_uuid = str(uuid.uuid4())
        file_name = source.name
        
        # Calculate file metadata
        file_size = source.stat().st_size
        mime_type, _ = mimetypes.guess_type(source)
        if mime_type is None:
            mime_type = "application/octet-stream"

        # Compute checksum
        sha256 = hashlib.sha256()
        with open(source, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        checksum = sha256.hexdigest()

        # Copy file to managed directory
        # Using UUID to prevent collisions
        dest_filename = f"{file_uuid}_{file_name}"
        dest_path = self.base_dir / dest_filename
        shutil.copy2(source, dest_path)

        # Create model and save
        attachment = Attachment(
            uuid=file_uuid,
            entity_type=entity_type,
            entity_id=entity_id,
            file_path=str(dest_path),
            file_name=file_name,
            mime_type=mime_type,
            file_size=file_size,
            checksum=checksum
        )
        
        return self.repository.create(attachment)

    def delete_attachment(self, attachment_id: int):
        # Soft delete in database
        self.repository.soft_delete(attachment_id)
        
        # Optionally, remove physical file immediately or keep it for recycle bin
        # Let's delete it to save space
        attachment = self.repository.get_by_id(attachment_id)
        if attachment and attachment.file_path:
            physical_path = Path(attachment.file_path)
            if physical_path.exists():
                try:
                    physical_path.unlink()
                except OSError as e:
                    print(f"Error removing file {physical_path}: {e}")
