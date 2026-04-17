param(
    [switch]$StagedOnly
)

$ErrorActionPreference = "Stop"

$repoRoot = (git rev-parse --show-toplevel).Trim()
Set-Location $repoRoot

$blockedPathPatterns = @(
    'C:\Users\',
    'AppData\',
    'OneDrive\',
    'Desktop\',
    'Downloads\',
    '/Users/',
    '/home/'
)

$secretPatterns = @(
    '(?i)\bapi[_-]?key\b\s*[:=]',
    '(?i)\btoken\b\s*[:=]',
    '(?i)\bpassword\b\s*[:=]',
    '(?i)\bsecret\b\s*[:=]',
    '(?i)authorization:\s*bearer\s+',
    '-----BEGIN (RSA |OPENSSH |DSA |EC |)PRIVATE KEY-----'
)

$blockedTrackedFiles = @(
    'evraklar.db',
    'sistem.log',
    '.env'
)

function Write-Failure($message) {
    Write-Host "[pre-commit] $message" -ForegroundColor Red
}

if ($StagedOnly) {
    $files = git diff --cached --name-only --diff-filter=ACMR
} else {
    $files = git ls-files
}

$files = @($files | Where-Object {
    $_ -and
    $_ -ne 'scripts/pre_commit_check.ps1' -and
    $_ -notmatch '(^|/)(build|dist|\.venv|venv|__pycache__|\.git)/' -and
    $_ -notmatch '\.(png|jpg|jpeg|gif|pdf|ico|exe|dll|pyd|db|sqlite|sqlite3)$'
})

$failed = $false

foreach ($file in $files) {
    $name = [System.IO.Path]::GetFileName($file)
    if ($blockedTrackedFiles -contains $name) {
        Write-Failure "Yasakli dosya commit'e giriyor: $file"
        $failed = $true
    }
}

foreach ($file in $files) {
    if (!(Test-Path -LiteralPath $file)) {
        continue
    }

    $content = Get-Content -LiteralPath $file -Raw -ErrorAction SilentlyContinue
    if ($null -eq $content) {
        continue
    }

    foreach ($pattern in $blockedPathPatterns) {
        if ($content -match [regex]::Escape($pattern)) {
            Write-Failure "Kisisel/mutlak yol bulundu: $file -> $pattern"
            $failed = $true
        }
    }

    foreach ($pattern in $secretPatterns) {
        if ($content -match $pattern) {
            Write-Failure "Secret/token benzeri ifade bulundu: $file -> $pattern"
            $failed = $true
        }
    }
}

if ($failed) {
    Write-Host ""
    Write-Host "Commit durduruldu. Once yukaridaki dosyalari temizleyin." -ForegroundColor Yellow
    exit 1
}

Write-Host "[pre-commit] Kontrol temiz." -ForegroundColor Green
