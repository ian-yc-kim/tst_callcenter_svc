import os
import uuid
import time
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File, status

# Import n8n integration components
from tst_callcenter_svc.routers.n8n_integration import N8nTriggerRequest, trigger_n8n_workflow

router = APIRouter()

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
ALLOWED_EXTENSIONS = ['.wav']
ALLOWED_MIME_TYPES = ['audio/wav', 'audio/x-wav']


def process_audio_file(file: UploadFile) -> dict:
    """
    Simulate audio processing (e.g., noise reduction).
    In a production scenario, this function would invoke an actual noise reduction library.
    Here we simply return a dummy processing result.
    """
    try:
        # Dummy processing simulation
        # For example, you might read portions of the file and process them.
        # file.file.seek(0)  # ensure at beginning if necessary
        # Simulate processing delay
        time.sleep(0.1)
        return {"status": "processed"}
    except Exception as e:
        logging.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Audio processing failed")


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Endpoint to handle secure file ingestion and audio preprocessing for recorded conversations.

    Validates the uploaded file (extension, MIME type, and size) and processes the audio file.
    Upon successful processing, triggers the n8n workflow integration with the processed file metadata.
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

        # Construct payload for n8n workflow integration
        upload_timestamp = datetime.utcnow()
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
