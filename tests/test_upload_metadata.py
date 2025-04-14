import uuid
from datetime import datetime

import pytest

from tst_callcenter_svc.models.upload_metadata import UploadMetadata


def test_create_upload_metadata(db_session):
    # Create a new upload_metadata record
    new_record = UploadMetadata(
        file_path='/uploads/test.txt',
        original_filename='test.txt',
        file_size=1024
    )
    db_session.add(new_record)
    db_session.commit()

    # Retrieve the record based on primary key
    record = db_session.query(UploadMetadata).filter_by(id=new_record.id).first()
    
    assert record is not None
    assert record.file_path == '/uploads/test.txt'
    assert record.original_filename == 'test.txt'
    assert record.file_size == 1024
    # Check that a default upload_timestamp is set
    assert record.upload_timestamp is not None
