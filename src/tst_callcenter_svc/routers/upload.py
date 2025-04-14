import os
import uuid
import time
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File, status, Depends

# Import n8n integration components
from tst_callcenter_svc.routers.n8n_integration import N8nTriggerRequest, trigger_n8n_workflow

# Import database dependencies and UploadMetadata model
from tst_callcenter_svc.models.upload_metadata import UploadMetadata
from tst_callcenter_svc.models.base import get_db

router = APIRouter()

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
ALLOWED_EXTENSIONS = ['.wav']
ALLOWED_MIME_TYPES = ['audio/wav', 'audio/x-wav']


def process_audio_file(file: UploadFile) -> dict:
    """
    Simulate audio processing (e.g., noise reduction).
    In a production scenario, this function would invoke an actual noise reduction library.
    Here we simply return a dummy processing result.

    Parameters:
        file (UploadFile): The uploaded audio file.

    Returns:
        dict: A dictionary containing processing status.
    """
    try:
        # Dummy processing simulation
        time.sleep(0.1)
        return {"status": "processed"}
    except Exception as e:
        logging.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Audio processing failed")


@router.post("/upload")
async def upload_file(file: UploadFile = File(...), db = Depends(get_db)):
    """
    Endpoint to handle secure file ingestion and audio preprocessing for recorded conversations.

    This endpoint validates the uploaded file (checking its extension, MIME type, and size),
    securely stores the file to disk, logs metadata in the database, processes the audio file,
    and triggers the n8n workflow integration.

    Parameters:
        file (UploadFile): The file to be uploaded. Must be a valid .wav file with MIME type 'audio/wav' or 'audio/x-wav'.
        db (Session): The SQLAlchemy database session provided via dependency injection.

    Returns:
        dict: Response from the n8n workflow trigger if the upload and logging are successful.

    Raises:
        HTTPException: For validation errors, disk write failures, or database insertion errors.
    """
    try:
        # Validate file existence
        if not file:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file uploaded")

        filename = file.filename
        if not any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file extension. Only .wav files are allowed")

        # Validate MIME type
        if file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid MIME type: {file.content_type}. Must be one of: {ALLOWED_MIME_TYPES}")

        # Validate file size
        try:
            file.file.seek(0, os.SEEK_END)
            file_size = file.file.tell()
            file.file.seek(0)
        except Exception as e:
            logging.error(e, exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not determine file size")

        if file_size > MAX_FILE_SIZE:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File size exceeds the maximum limit of 100MB")

        # Process the audio file (simulate noise reduction etc.)
        processing_result = process_audio_file(file)

        # Generate unique filename and determine storage directory
        storage_dir = os.getenv("FILE_STORAGE_PATH", "secure_uploads")
        try:
            os.makedirs(storage_dir, exist_ok=True)
        except Exception as e:
            logging.error(e, exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create storage directory")

        unique_filename = f"{uuid.uuid4()}.wav"
        full_file_path = os.path.join(storage_dir, unique_filename)

        # Write file content securely to disk
        try:
            file_content = await file.read()
            with open(full_file_path, "wb") as f:
                f.write(file_content)
        except Exception as e:
            logging.error(e, exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Disk write error")

        # Log metadata in the database with rollback on failure
        upload_timestamp = datetime.utcnow()
        try:
            metadata_record = UploadMetadata(
                file_path=full_file_path,
                original_filename=filename,
                file_size=file_size,
                upload_timestamp=upload_timestamp
            )
            db.add(metadata_record)
            db.commit()
        except Exception as e:
            db.rollback()
            logging.error(e, exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database insertion error")

        # Construct payload for n8n workflow integration
        payload = N8nTriggerRequest(
            file_name=filename,
            file_size=file_size,
            upload_timestamp=upload_timestamp,
            metadata={"processing_status": processing_result.get("status", "unknown")}
        )

        # Trigger n8n workflow integration
        response = trigger_n8n_workflow(payload)

        return response
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logging.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
