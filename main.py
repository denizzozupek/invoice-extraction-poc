import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from models import Invoice
from ai import extract_invoice_data
import logging
import shutil
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("api.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI-Powered Invoice Extraction API",
    description="An API to extract structured data from invoices using AI.",
    version="0.1.0"
)

@app.post("/api/v0.1/invoice-extraction", response_model=Invoice)
def ainvoice_extraction(file: UploadFile = File(...)):
    """
    Takes Invoice from user and returns structured data extracted from the invoice using AI. The endpoint accepts a file upload, processes the invoice, and returns the extracted data in a structured format defined by the Invoice model.
    """
    allowed_extensions = ["image/jpeg", "image/png", "image/jpg", "application/pdf"]
    if file.content_type not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Unsupported file type. Please upload a JPEG, PNG, PDF, or DOCX file.")
    
    safe_filename = file.filename.replace(" ", "_")
    temp_file_path = f"temp_{safe_filename}"
    
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"File {file.filename} uploaded successfully. Starting extraction process.")
        result_invoice = extract_invoice_data(temp_file_path)

        if not result_invoice:
            raise HTTPException(status_code=500, detail="Failed to extract data from the invoice. Please try again.")
        logger.info(f"Data extraction successful for file {file.filename}. Returning structured data.")
        return result_invoice
    except Exception as e:
        logger.error(f"Error processing file {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while processing the invoice. Please try again.")
    finally:
        try:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                logger.info(f"Temporary file {temp_file_path} removed successfully.")
        except Exception as e:
            logger.warning(f"Could not remove temporary file {temp_file_path}: {str(e)}")
