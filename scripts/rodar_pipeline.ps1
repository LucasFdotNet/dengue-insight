# Roda o pipeline completo (src/pipeline_completo.py) em segundo plano, sem deixar o Windows
# suspender enquanto ele roda.
#
# O pipeline roda num processo independente: fechar o terminal ou o editor não o interrompe.
# Enquanto ele estiver vivo, um segundo processo pede ao Windows para não suspender o sistema
# (SetThreadExecutionState, a mesma API usada por players de vídeo). A tela ainda pode
# apagar. Nenhuma configuração de energia é alterada, e o pedido some quando o pipeline termina.
#
# Uso (na raiz do projeto):
#   powershell -ExecutionPolicy Bypass -File scripts\rodar_pipeline.ps1            dados atuais (ou continua)
#   powershell -ExecutionPolicy Bypass -File scripts\rodar_pipeline.ps1 --baixar   baixa os dados antes
#
# Acompanhar:  Get-Content reports\logs\pipeline.log -Wait
# Conferir que o Windows não vai suspender:  powercfg /requests   (aparece em SYSTEM)
# Num notebook: deixe na tomada e, se for fechar a tampa, configure "fechar a tampa: não fazer nada".

$raiz = Split-Path -Parent $PSScriptRoot
$python = Join-Path $raiz 'venv\Scripts\python.exe'
$logs = Join-Path $raiz 'reports\logs'
New-Item -ItemType Directory -Force $logs | Out-Null

$argumentos = @('-m', 'src.pipeline_completo') + $args
$pipeline = Start-Process -FilePath $python -ArgumentList $argumentos -WorkingDirectory $raiz -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logs 'pipeline_saida.log') -RedirectStandardError (Join-Path $logs 'pipeline.log') `
    -PassThru

$acordado = @"
Add-Type -Namespace Win32 -Name Energia -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint f);'
[Win32.Energia]::SetThreadExecutionState(0x80000001) | Out-Null   # ES_CONTINUOUS | ES_SYSTEM_REQUIRED
while (Get-Process -Id $($pipeline.Id) -ErrorAction SilentlyContinue) { Start-Sleep -Seconds 60 }
"@
Start-Process -FilePath powershell.exe -ArgumentList '-NoProfile', '-WindowStyle', 'Hidden', '-Command', $acordado `
    -WindowStyle Hidden | Out-Null

Write-Output "Pipeline iniciado (processo $($pipeline.Id)); o Windows não suspende até ele terminar."
Write-Output "Log: reports\logs\pipeline.log"
