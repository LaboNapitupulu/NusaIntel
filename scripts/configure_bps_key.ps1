$ErrorActionPreference = 'Stop'

$secureKey = Read-Host 'Masukkan BPS API key' -AsSecureString
$keyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)

try {
    $plainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer)
    if ([string]::IsNullOrWhiteSpace($plainKey)) {
        throw 'BPS API key tidak boleh kosong.'
    }
    if ($plainKey.Contains("`r") -or $plainKey.Contains("`n")) {
        throw 'BPS API key tidak boleh mengandung baris baru.'
    }

    $projectRoot = Split-Path -Parent $PSScriptRoot
    $envPath = Join-Path $projectRoot '.env'
    $envContent = "BPS_API_KEY=$plainKey`n"
    $utf8NoBom = New-Object System.Text.UTF8Encoding -ArgumentList $false
    [System.IO.File]::WriteAllText($envPath, $envContent, $utf8NoBom)

    Write-Output "BPS API key tersimpan di $envPath"
    Write-Output 'Nilai key tidak ditampilkan dan file .env diabaikan oleh Git.'
}
finally {
    if ($keyPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer)
    }
    $plainKey = $null
    $secureKey = $null
    $utf8NoBom = $null
}
