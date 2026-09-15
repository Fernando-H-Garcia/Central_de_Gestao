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

    def move_attachment(self, attachment_id: int, target_entity_type: str, target_entity_id: int) -> Attachment:
        att = self.repository.get_by_id(attachment_id)
        if not att:
            raise ValueError("Anexo não encontrado")
        att.entity_type = target_entity_type
        att.entity_id = target_entity_id
        return self.repository.update(att)

    def rename_attachment(self, attachment_id: int, new_file_name: str) -> Attachment:
        new_file_name = (new_file_name or "").strip()
        if not new_file_name:
            raise ValueError("Nome do arquivo não pode ser vazio")
        # sanitiza: remove separadores de caminho
        new_file_name = new_file_name.replace("\\", "_").replace("/", "_")
        if not new_file_name:
            raise ValueError("Nome inválido")
        att = self.repository.get_by_id(attachment_id)
        if not att:
            raise ValueError("Anexo não encontrado")
        # ── preserva o formato/extensão original (não deixa alterar) ──
        old_ext = Path(att.file_name).suffix if getattr(att, 'file_name', None) else ""
        # extrai apenas a base do nome informado, descartando extensão digitada
        input_path = Path(new_file_name)
        if input_path.suffix:
            new_base = input_path.stem
        else:
            new_base = new_file_name
        new_base = new_base.strip().replace("\\", "_").replace("/", "_")
        if not new_base:
            raise ValueError("Nome inválido")
        # reconstrói com a extensão original (formato inalterado)
        final_name = f"{new_base}{old_ext}" if old_ext else new_base
        if final_name == att.file_name:
            return att
        new_file_name = final_name
        # tenta renomear arquivo físico mantendo prefixo uuid_ se existir
        try:
            old_path = Path(att.file_path) if att.file_path else None
            if old_path and old_path.exists():
                # preserva diretório, renomeia parte após uuid_
                new_dest_name = f"{att.uuid}_{new_file_name}"
                new_path = old_path.parent / new_dest_name
                # se o arquivo já tem o mesmo nome, não precisa mover
                if old_path.resolve() != new_path.resolve():
                    # evita sobrescrever: se destino existe, adiciona sufixo antes da extensão original
                    if new_path.exists():
                        stem = Path(new_file_name).stem
                        suffix = Path(new_file_name).suffix  # == old_ext
                        counter = 1
                        while new_path.exists():
                            alt_name = f"{stem} ({counter}){suffix}"
                            new_path = old_path.parent / f"{att.uuid}_{alt_name}"
                            counter += 1
                            # atualiza new_file_name para refletir o nome real salvo
                            new_file_name = alt_name
                    old_path.rename(new_path)
                    att.file_path = str(new_path)
        except Exception:
            # falha no FS não deve impedir atualização do nome lógico
            pass
        att.file_name = new_file_name
        # mime permanece o mesmo pois extensão não muda; mantém atualização defensiva
        mt, _ = mimetypes.guess_type(new_file_name)
        if mt:
            att.mime_type = mt
        return self.repository.update(att)

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
