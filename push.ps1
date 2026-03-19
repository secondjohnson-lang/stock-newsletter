cd C:\Users\Firstmouse\Desktop\AI_Projects

$status = git status --short

if (-not $status) {
    Write-Host "Nothing to commit." -ForegroundColor Yellow
    pause
    exit
}

git add .
$diff = git diff --cached --stat

$prompt = "You are a developer writing a git commit message. Based on these file changes, write a single clear commit message under 10 words that describes what was updated. No preamble, no quotes, just the message.`n`nChanges:`n$diff"

$body = @{
    model      = "openrouter/hunter-alpha"
    messages   = @(
        @{ role = "user"; content = $prompt }
    )
    max_tokens = 50
} | ConvertTo-Json -Depth 5

$headers = @{
    "Authorization" = "Bearer $env:OPENROUTER_API_KEY"
    "Content-Type"  = "application/json"
}

Write-Host "Generating commit message..." -ForegroundColor Cyan

try {
    $response = Invoke-RestMethod -Uri "https://openrouter.ai/api/v1/chat/completions" -Method Post -Headers $headers -Body $body
    $message = $response.choices[0].message.content.Trim()
}
catch {
    $message = "Update project files"
}

Write-Host "Commit message: $message" -ForegroundColor Green

git commit -m $message
git push origin main

Write-Host "`nPushed successfully" -ForegroundColor Green
pause