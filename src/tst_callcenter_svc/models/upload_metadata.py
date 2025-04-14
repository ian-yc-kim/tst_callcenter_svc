import uuid

from sqlalchemy import Column, Integer, Text, DateTime, func
from sqlalchemy.types import String

from tst_callcenter_svc.models.base import Base


class UploadMetadata(Base):
    __tablename__ = 'upload_metadata'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_path = Column(Text, nullable=False)
    original_filename = Column(Text, nullable=False)
    file_size = Column(Integer, nullable=False)
    upload_timestamp = Column(DateTime, nullable=False, server_default=func.now())
