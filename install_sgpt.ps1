$ErrorActionPreference = "Stop"

$Repo = "https://raw.githubusercontent.com/gl1ndy/cli-sekret-gpt/main"
$Dir = "$env:LOCALAPPDATA\SecretGPT"
$Bin = "$Dir\bin"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python 3 is not installed or not in PATH." -ForegroundColor Red
    exit 1
}

New-Item -ItemType Directory -Force -Path $Dir, $Bin | Out-Null

Invoke-WebRequest "$Repo/mini_ai_chat.py" -OutFile "$Dir\mini_ai_chat.py"

@"
@echo off
python "%LOCALAPPDATA%\SecretGPT\mini_ai_chat.py" %*
"@ | Set-Content "$Bin\sgpt.cmd" -Encoding ASCII

$Path = [Environment]::GetEnvironmentVariable("Path", "User")
if (($Path -split ";") -notcontains $Bin) {
    [Environment]::SetEnvironmentVariable("Path", "$Path;$Bin", "User")
}

Write-Host "`nInstalled! Reopen PowerShell and run: sgpt" -ForegroundColor Green