# Démarrer le chatbot IA sur le PORT 8001 (livraison_app est sur 8000)
# Exécuter depuis un nouveau terminal PowerShell

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

$chatbotPath = "C:\Users\Admin\Documents\agent_Ia_finale"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Chatbot IA → http://localhost:8001" -ForegroundColor Cyan
Write-Host "  (livraison_app reste sur port 8000)" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan

Set-Location $chatbotPath

# PORT 8001 pour eviter le conflit avec livraison_app (port 8000)
uvicorn api_generale:app --host 0.0.0.0 --port 8001
