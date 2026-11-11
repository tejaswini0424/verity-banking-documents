# Local installation

Use the two-terminal setup in README.md. Run commands from this repository root, which contains `backend/` and `frontend/`.

## Configuration

Backend reads environment variables from the process. To load `.env` with Uvicorn, install `python-dotenv` and pass `--env-file .env`, or set variables directly in PowerShell:

```powershell
$env:OLLAMA_MODEL = 'your-installed-vision-model'
$env:OLLAMA_URL = 'http://127.0.0.1:11434'
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 48123
```

Leave OLLAMA_MODEL unset for the baseline. The default SQLite database uses the repository's storage directory. If you set a relative DATABASE_URL, launch from the repository root.

For scanned-image OCR install the official Tesseract executable separately. The backend discovers TESSERACT_CMD, PATH, or the standard Windows Program Files/Tesseract-OCR location. The Python pytesseract package alone does not provide the executable. Text-bearing PDFs do not require Tesseract. Docker installs Tesseract inside its image.

Local frontend uses port 5178, backend 48123. If changing ports, update frontend/vite.config.ts and ALLOWED_ORIGINS. The API docs link currently points at the documented local backend port. No seeded credentials are provided.
