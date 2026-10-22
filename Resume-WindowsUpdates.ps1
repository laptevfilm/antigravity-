# Скрипт для отмены приостановки обновлений Windows (возобновление обновлений).
# Запустите этот скрипт в PowerShell от имени Администратора.

$RegPath = "HKLM:\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings"

$KeysToRemove = @(
    "PauseUpdatesStartTime",
    "PauseUpdatesExpiryTime",
    "PauseFeatureUpdatesStartTime",
    "PauseFeatureUpdatesEndTime",
    "PauseQualityUpdatesStartTime",
    "PauseQualityUpdatesEndTime",
    "PauseUXUpdatesStartTime",
    "PauseUXUpdatesEndTime"
)

Write-Host "Возобновляем автоматические обновления Windows..." -ForegroundColor Cyan

foreach ($Key in $KeysToRemove) {
    if (Get-ItemProperty -Path $RegPath -Name $Key -ErrorAction SilentlyContinue) {
        Remove-ItemProperty -Path $RegPath -Name $Key -Force | Out-Null
    }
}

Write-Host "Готово! Пауза обновлений снята." -ForegroundColor Green
