from openai import OpenAI
from dotenv import load_dotenv
import os
import base64
from pathlib import Path
from models import Invoice
import json

# Load environment variables
load_dotenv()

class InvoiceExtractor:
    def __init__(self):
        """Initialize the OpenAI client with API key from .env"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in .env file")
        
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-5-nano"
        
    def encode_image(self, image_path: str) -> str:
        """Encode image to base64 string"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def extract_from_image(self, image_path: str) -> Invoice:
        """
        Extract invoice data from an image file
        
        Args:
            image_path: Path to the invoice image (jpg, png, pdf, etc.)
            
        Returns:
            Invoice: Validated Pydantic Invoice object
        """
        if not Path(image_path).exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # Encode image
        base64_image = self.encode_image(image_path)
        
        # Determine image type
        ext = Path(image_path).suffix.lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.webp': 'image/webp',
            '.gif': 'image/gif'
        }
        mime_type = mime_types.get(ext, 'image/jpeg')
        
        # Create the prompt
        prompt = self._create_extraction_prompt()
        
        # Call OpenAI API (temperature parametresini kaldırdık)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert invoice data extraction assistant. Extract all relevant information from invoices accurately and return it as valid JSON that matches the provided schema."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse response
        json_data = json.loads(response.choices[0].message.content)
        
        # Validate and return Invoice object
        return Invoice(**json_data)
    
    def extract_from_text(self, invoice_text: str) -> Invoice:
        """
        Extract invoice data from text content
        
        Args:
            invoice_text: Text content of the invoice
            
        Returns:
            Invoice: Validated Pydantic Invoice object
        """
        prompt = self._create_extraction_prompt()
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert invoice data extraction assistant. Extract all relevant information from invoices accurately and return it as valid JSON that matches the provided schema."
                },
                {
                    "role": "user",
                    "content": f"{prompt}\n\nInvoice Content:\n{invoice_text}"
                }
            ],
            response_format={"type": "json_object"}
        )
        
        json_data = json.loads(response.choices[0].message.content)
        return Invoice(**json_data)
    
    def _create_extraction_prompt(self) -> str:
        """Create the extraction prompt with schema details"""
        return """Extract all invoice information from the provided image/text and return it as a JSON object.

CRITICAL REQUIREMENTS:
1. Extract ALL visible information from the invoice
2. For Turkish invoices, extract: ettn, vkn_tckn, company_tax_office, ticaret_sicil_no, district, neighborhood
3. For each item, extract: description, quantity, unit_price, tax_rate, tax_amount, discount_amount, discount_rate
4. Calculate amounts following this hierarchy: gross_amount -> net_amount -> total_amount
5. Always provide at minimum: quantity + unit_price OR total_amount for each item
6. Tax rates should be decimal (e.g., 0.20 for 20% or 20 if shown as percentage - the model will normalize)
7. All monetary values should be Decimal-compatible strings or numbers
8. Dates must be in YYYY-MM-DD format
9. Currency must be a 3-letter code (e.g., TRY, USD, EUR)

INVOICE TYPES (invoice_type field):
- Turkish invoices: "SATIS" (sale), "IADE" (return), "TEVKIFAT" (withholding)
- International: "standard", "proforma", "credit_note", etc.

AMOUNT CALCULATION LOGIC:
- gross_amount = quantity × unit_price
- net_amount = gross_amount - discount_amount
- total_amount = net_amount + tax_amount

If any field is not visible or not applicable, use null (except for required fields).

Return a valid JSON object matching this structure:
{
    "invoice_number": "string",
    "invoice_date": "YYYY-MM-DD",
    "due_date": "YYYY-MM-DD or null",
    "invoice_type": "string or null",
    "company_name": "string",
    "company_address": {
        "street": "string or null",
        "city": "string or null",
        "zip_code": "string or null",
        "country": "string or null",
        "district": "string or null (for TR)",
        "neighborhood": "string or null (for TR)"
    },
    "company_tax_info": "string or null",
    "company_tax_office": "string or null (for TR)",
    "customer_name": "string or null",
    "customer_address": {
        "street": "string or null",
        "city": "string or null",
        "zip_code": "string or null",
        "country": "string or null",
        "district": "string or null (for TR)",
        "neighborhood": "string or null (for TR)"
    },
    "customer_tax_info": "string or null",
    "ettn": "string or null (for TR e-invoices)",
    "vkn_tckn": "string or null (for TR)",
    "ticaret_sicil_no": "string or null (for TR)",
    "items": [
        {
            "description": "string",
            "quantity": "number or null",
            "unit_price": "number or null",
            "tax_rate": "number or null",
            "tax_amount": "number or null",
            "discount_amount": "number or null",
            "discount_rate": "number or null",
            "gross_amount": "number or null",
            "net_amount": "number or null",
            "total_amount": "number or null",
            "tevkifat_rate": "number or null (for TR)"
        }
    ],
    "subtotal": "number or null",
    "total_discount": "number or null",
    "total_tax": "number or null",
    "total_amount": "number",
    "currency": "string (3 letters)"
}

IMPORTANT: Make sure to extract numbers accurately, including decimals. Do not add or modify any values."""

def extract_invoice_data(file_path: str) -> Invoice:
    """Helper function to create an instance of InvoiceExtractor and extract data from the given file path"""
    extractor = InvoiceExtractor()
    ext = Path(file_path).suffix.lower()
    
    if ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.pdf']:
        return extractor.extract_from_image(file_path)
    else:
        raise ValueError(f"Unsupported file type for extraction: {ext}")

        