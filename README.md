```markdown
# 🧾 AI Invoice Extraction POC

![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?style=for-the-badge&logo=fastapi)
![Docker](https://img.shields.io/badge/Docker-Available-2496ED?style=for-the-badge&logo=docker)
![OpenAI](https://img.shields.io/badge/AI-GPT--4o-412991?style=for-the-badge&logo=openai)

##  Project Overview 

**AI Invoice Extraction POC** is a specialized REST API designed to extract structured data from unstructured invoice images (JPG, PNG) using **OpenAI's** vision capabilities.

This project serves as a **technical showcase** demonstrates the integration of Large Language Models (LLMs) into a robust backend architecture. It emphasizes **Type Safety**, **Containerization**, and **Modern API Standards**.

### Key Learning Outcomes & Technical Goals
This project was engineered to explore and implement:
* **AI Integration:** Wrapping OpenAI API to function as a deterministic data extractor.
* **Data Validation:** Using **Pydantic** to enforce strict schemas (ensuring strings are strings, amounts are decimals).
* **Containerization:** Full **Docker** support for "Build once, run anywhere" capability.
* **Modern Backend:** Asynchronous API development with **FastAPI**.

---

## 🛠️ Tech Stack

* **Core Framework:** FastAPI 
* **AI Model:** OpenAI GPT
* **Validation:** Pydantic V2
* **Container:** Docker (Slim-based Python Image)
* **Testing:** Pytest

---

## Limitations & MVP Status

> **Engineering Note:** This is a **Proof of Concept (PoC)** / MVP v0.1. It is designed for demonstration and learning purposes, not for production-grade financial operations without further refinement.

* **File Support:** Currently supports image formats (JPG, PNG). PDF support is in the roadmap.
* **Security:** This MVP uses basic API key management. Production deployment would require OAuth2 or JWT authentication.

---

## Quick Start

### Prerequisites
* Docker installed
* An OpenAI API Key

### 1. Clone the Repository
```bash
git clone [https://github.com/denizzozupek/invoice-extraction-poc.git](https://github.com/denizzozupek/invoice-extraction-poc.git)
cd invoice-extraction-poc

```

### 2. Configure Environment

Create a `.env` file in the root directory:

```env
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxx

```

### 3. Build & Run with Docker 🐳

No need to install Python dependencies manually. Just use Docker:

```bash
# Build the image
docker build -t invoice-poc .

# Run the container
docker run -d -p 8000:8000 --env-file .env --name invoice-api invoice-poc

```

### 4. Test the API

Open your browser and navigate to the auto-generated Swagger UI:
👉 **http://localhost:8000/docs**

1. Click on `/extract-invoice` endpoint.
2. Click **Try it out**.
3. Upload an invoice image.
4. Execute and see the JSON.

---

## Example Output

The API converts an image into this structured JSON:

```json
{
  "invoice_number": "FAT-2024-001",
  "date": "2024-02-16",
  "total_amount": 1250.50,
  "currency": "TRY",
  "items": [
    {
      "description": "Consulting Services",
      "quantity": 5,
      "unit_price": 250.10,
      "total": 1250.50
    }
  ]
}

```

---

## 📝 License

This project is open-source and available under the [MIT License](https://www.google.com/search?q=LICENSE).

