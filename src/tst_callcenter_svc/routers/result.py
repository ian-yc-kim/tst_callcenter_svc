import uuid
import os
import logging
import requests
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session

from tst_callcenter_svc.models.upload_metadata import UploadMetadata
from tst_callcenter_svc.models.base import get_db


router = APIRouter()


@router.get("/result/{upload_id}")
def get_result(upload_id: str, db: Session = Depends(get_db)):
    # Validate that upload_id is a valid UUID
    try:
        uuid_obj = uuid.UUID(upload_id)
    except ValueError as e:
        logging.error("Invalid UUID format", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid UUID format")

    # Query the database for the upload record
    try:
        record = db.query(UploadMetadata).filter(UploadMetadata.id == upload_id).first()
    except Exception as e:
        logging.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")

    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload record not found")

    # Retrieve Airtable configuration from environment variables
    airtable_api_url = os.getenv("AIRTABLE_API_URL")
    airtable_api_key = os.getenv("AIRTABLE_API_KEY")
    airtable_base_id = os.getenv("AIRTABLE_BASE_ID")
    airtable_table_name = os.getenv("AIRTABLE_TABLE_NAME")

    if not all([airtable_api_url, airtable_api_key, airtable_base_id, airtable_table_name]):
        logging.error("Missing one or more Airtable configuration environment variables")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Missing Airtable configuration")

    # Construct Airtable GET request
    # Format: {AIRTABLE_API_URL}/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}?filterByFormula=AND({UploadID}='{upload_id}')
    filter_formula = f"AND({{UploadID}}='{upload_id}')"
    params = {"filterByFormula": filter_formula}
    headers = {"Authorization": f"Bearer {airtable_api_key}"}

    try:
        response = requests.get(f"{airtable_api_url}/{airtable_base_id}/{airtable_table_name}", params=params, headers=headers, timeout=10)
        if response.status_code != 200:
            logging.error(f"Airtable API error: Status code {response.status_code}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error retrieving analysis details from Airtable")
        airtable_data = response.json()
    except Exception as e:
        logging.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error retrieving analysis details from Airtable")

    records = airtable_data.get("records")
    if not records or len(records) == 0:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Analysis details not found in Airtable")

    # Extract required fields from the first matching record
    fields = records[0].get("fields", {})
    processing_status = fields.get("processing_status")
    logs_val = fields.get("logs")
    analysis_result = fields.get("analysis_result")

    # Construct and return the response
    return {
        "upload_id": record.id,
        "original_filename": record.original_filename,
        "file_size": record.file_size,
        "upload_timestamp": record.upload_timestamp.isoformat(),
        "processing_status": processing_status,
        "logs": logs_val,
        "analysis_result": analysis_result
    }
