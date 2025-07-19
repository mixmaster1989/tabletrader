# Скрипт для остановки Google Signals Bot
Write-Host "🛑 Останавливаю Google Signals Bot..." -ForegroundColor Red

# Находим все процессы Python
$pythonProcesses = Get-Process | Where-Object {$_.ProcessName -like "*python*"}

if ($pythonProcesses) {
    Write-Host "📋 Найдено процессов Python: $($pythonProcesses.Count)" -ForegroundColor Yellow
    
    foreach ($process in $pythonProcesses) {
        Write-Host "🔄 Останавливаю процесс: $($process.ProcessName) (PID: $($process.Id))" -ForegroundColor Cyan
        try {
            Stop-Process -Id $process.Id -Force
            Write-Host "✅ Процесс $($process.Id) остановлен" -ForegroundColor Green
        }
        catch {
            Write-Host "❌ Ошибка при остановке процесса $($process.Id): $($_.Exception.Message)" -ForegroundColor Red
        }
    }
} else {
    Write-Host "ℹ️ Процессы Python не найдены" -ForegroundColor Blue
}

# Дополнительная проверка через taskkill
Write-Host "🔍 Дополнительная проверка через taskkill..." -ForegroundColor Yellow
try {
    $result = taskkill /f /im python.exe 2>&1
    Write-Host "✅ taskkill выполнен" -ForegroundColor Green
} catch {
    Write-Host "ℹ️ taskkill: $result" -ForegroundColor Blue
}

# Финальная проверка
Start-Sleep -Seconds 2
$remainingProcesses = Get-Process | Where-Object {$_.ProcessName -like "*python*"}

if ($remainingProcesses) {
    Write-Host "⚠️ Остались процессы Python: $($remainingProcesses.Count)" -ForegroundColor Yellow
    foreach ($process in $remainingProcesses) {
        Write-Host "  - $($process.ProcessName) (PID: $($process.Id))" -ForegroundColor Yellow
    }
} else {
    Write-Host "🎉 Все процессы Python успешно остановлены!" -ForegroundColor Green
}

Write-Host "✅ Скрипт завершен" -ForegroundColor Green 