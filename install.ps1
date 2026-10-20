# Windows Installer for gdoc-ai-bridge
param(
    [string]$CredentialsPath = ""
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Installing gdoc-ai-bridge (Windows)     " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Check Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "[ERROR] Python is not installed or not in PATH." -ForegroundColor Red
    exit 1
}
Write-Host "[+] Found Python: $($pythonCmd.Source)" -ForegroundColor Green

# 2. Install dependencies
Write-Host "[*] Installing Python dependencies..." -ForegroundColor Yellow
python -m pip install -r "$PSScriptRoot\requirements.txt" --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to install dependencies." -ForegroundColor Red
    exit 1
}
Write-Host "[+] Dependencies installed successfully." -ForegroundColor Green

# 3. Create ~/.gdoc directory
$gdocHome = "$HOME\.gdoc"
$gdocBin = "$gdocHome\bin"
New-Item -ItemType Directory -Path $gdocHome -Force | Out-Null
New-Item -ItemType Directory -Path $gdocBin -Force | Out-Null

# Copy global engine and launcher scripts
Copy-Item "$PSScriptRoot\src\gdoc_ai\cli.py" -Destination "$gdocHome\gdoc_tool.py" -Force
Copy-Item "$PSScriptRoot\bin\*" -Destination $gdocBin -Force

# 4. Handle credentials
if ($CredentialsPath -and (Test-Path $CredentialsPath)) {
    Copy-Item $CredentialsPath -Destination "$gdocHome\credentials.json" -Force
    Write-Host "[+] Copied credentials from $CredentialsPath" -ForegroundColor Green
} elseif (Test-Path "credentials.json") {
    Copy-Item "credentials.json" -Destination "$gdocHome\credentials.json" -Force
    Write-Host "[+] Copied local credentials.json to $gdocHome" -ForegroundColor Green
}

# 5. Add to User PATH
$userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($userPath -notlike "*$gdocBin*") {
    $newUserPath = $userPath.TrimEnd(';') + ";$gdocBin"
    [Environment]::SetEnvironmentVariable("PATH", $newUserPath, "User")
    Write-Host "[+] Added $gdocBin to permanent User PATH." -ForegroundColor Green
} else {
    Write-Host "[+] $gdocBin is already in User PATH." -ForegroundColor Green
}

# Also update current session PATH
$env:PATH = "$env:PATH;$gdocBin"

Write-Host "`n[+] Installation complete!" -ForegroundColor Cyan
Write-Host "Next steps:" -ForegroundColor White
Write-Host "1. Save your Google Cloud OAuth JSON as: $gdocHome\credentials.json"
Write-Host "2. In a new terminal, run: gdoc auth"
Write-Host "3. Start reading & editing Docs and Sheets via AI!"
