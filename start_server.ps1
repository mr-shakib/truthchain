Set-Location "D:\Personal\Project\AI-Engineering\ai-labs\truthchain"
$env:PYTHONPATH = "D:\Personal\Project\AI-Engineering\ai-labs\truthchain"
$env:GROQ_API_KEY = "YOUR_GROQ_API_KEY_HERE"
Write-Host "[start_server] PYTHONPATH=$env:PYTHONPATH"
Write-Host "[start_server] GROQ_API_KEY=$($env:GROQ_API_KEY.Substring(0,12))..."
& "D:\Personal\Project\AI-Engineering\ai-labs\truthchain\venv\Scripts\python.exe" -m uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
