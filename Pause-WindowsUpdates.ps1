# Скрипт для приостановки обновлений Windows на 30 дней.
# Запустите этот скрипт в PowerShell от имени Администратора.

$DaysToPause = 30
$Now = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$Expiry = (Get-Date).AddDays($DaysToPause).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

$RegPath = "HKLM:\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings"

Write-Host "Настраиваем приостановку обновлений Windows на $DaysToPause дней (до $Expiry UTC)..." -ForegroundColor Cyan

if (!(Test-Path $RegPath)) {
    New-Item -Path $RegPath -Force | Out-Null
}

# Устанавливаем ключи приостановки обновлений
Set-ItemProperty -Path $RegPath -Name "PauseUpdatesStartTime" -Value $Now -Force
Set-ItemProperty -Path $RegPath -Name "PauseUpdatesExpiryTime" -Value $Expiry -Force
Set-ItemProperty -Path $RegPath -Name "PauseFeatureUpdatesStartTime" -Value $Now -Force
Set-ItemProperty -Path $RegPath -Name "PauseFeatureUpdatesEndTime" -Value $Expiry -Force
Set-ItemProperty -Path $RegPath -Name "PauseQualityUpdatesStartTime" -Value $Now -Force
Set-ItemProperty -Path $RegPath -Name "PauseQualityUpdatesEndTime" -Value $Expiry -Force
Set-ItemProperty -Path $RegPath -Name "PauseUXUpdatesStartTime" -Value $Now -Force
Set-ItemProperty -Path $RegPath -Name "PauseUXUpdatesEndTime" -Value $Expiry -Force

Write-Host "Готово! Автообновления успешно приостановлены на $DaysToPause дней." -ForegroundColor Green
Write-Host "Вы можете проверить статус в 'Параметры -> Центр обновления Windows'." -ForegroundColor Yellow
