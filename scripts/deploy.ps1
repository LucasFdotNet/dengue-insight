# Publica o painel estático (web/) na branch deploy, de onde o Cloudflare Pages faz o deploy.
#
# O build de web/ é feito a partir de uma branch (main, por padrão) numa cópia temporária
# (git worktree), sem mexer na pasta de trabalho. O conteúdo de web/dist vira um novo commit na
# branch deploy, que só contém o site pronto (index.html, assets/, dados/, _headers). Antes do
# commit e do push, o script mostra o que muda e pede confirmação. Ao receber o push, o
# Cloudflare publica sozinho.
#
# Entra no site o que está commitado na branch de origem; mudanças não commitadas ficam de fora.
# A branch deploy não pode estar aberta nesta pasta (ela não tem o código, só o site).
#
# Uso (na raiz do projeto):
#   powershell -ExecutionPolicy Bypass -File scripts\deploy.ps1                   build da main
#   powershell -ExecutionPolicy Bypass -File scripts\deploy.ps1 -Origem revisao   build de outra branch

param([string]$Origem = 'main')

[Console]::OutputEncoding = [Text.Encoding]::UTF8
$destino = 'deploy'
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

# Roda um programa e interrompe o script se ele falhar (o stderr dos programas não é tratado como erro)
function Rodar {
    $programa, $argumentos = $args
    & $programa @argumentos
    if ($LASTEXITCODE) { throw "Falhou: $programa $argumentos" }
}

if ((git branch --show-current) -eq $destino) {
    throw "A branch $destino está aberta nesta pasta. Troque de branch antes (git switch main)."
}

Rodar git fetch origin --quiet
$commitOrigem = Rodar git rev-parse --verify --quiet "$Origem^{commit}"
$resumoOrigem = Rodar git log -1 --format='%h %s' $commitOrigem
if ((git rev-parse --verify --quiet "origin/$Origem^{commit}") -ne $commitOrigem) {
    Write-Warning "$Origem local difere de origin/$Origem (falta push ou pull?)."
}
$pai = git rev-parse --verify --quiet "origin/$destino^{commit}"   # vazio se a branch ainda não existe
$gitDir = Rodar git rev-parse --absolute-git-dir

$temp = Join-Path ([IO.Path]::GetTempPath()) "dengue-deploy-$PID"
$indice = "$temp-indice"
try {
    Write-Output "Gerando o site a partir de $Origem ($resumoOrigem)..."
    Rodar git worktree add --detach --quiet $temp $commitOrigem
    Push-Location (Join-Path $temp 'web')
    try {
        Rodar npm.cmd ci --no-audit --no-fund
        Rodar npm.cmd run build
    } finally { Pop-Location }

    # Monta a árvore do commit com o conteúdo de web/dist, num índice à parte (não toca no índice do repositório)
    $dist = Join-Path $temp 'web\dist'
    $env:GIT_INDEX_FILE = $indice
    try {
        Rodar git -C $dist --git-dir=$gitDir --work-tree=$dist add --all --force .
        $arvore = Rodar git --git-dir=$gitDir write-tree
    } finally { Remove-Item Env:GIT_INDEX_FILE }

    if ($pai -and (git rev-parse "$pai^{tree}") -eq $arvore) {
        Write-Output "O site gerado é igual ao que já está em $destino; nada a publicar."
        return
    }

    Write-Output ''
    if ($pai) {
        Write-Output "Mudanças em relação a origin/${destino}:"
        $mudancas = @(git diff --name-status $pai $arvore)
        $mudancas | Select-Object -First 20 | ForEach-Object { "  $_" }
        if ($mudancas.Count -gt 20) { Write-Output "  ... e mais $($mudancas.Count - 20) arquivos" }
        git diff --shortstat $pai $arvore
    } else {
        Write-Output "A branch $destino ainda não existe no GitHub; será criada."
    }
    Write-Output ''
    $resposta = Read-Host "Publicar $Origem ($resumoOrigem) na branch $destino? [s/N]"
    if ($resposta -notmatch '^\s*(s|sim)\s*$') {
        Write-Output 'Cancelado; nada foi alterado.'
        return
    }

    $mensagem = "deploy: painel gerado de $Origem ($($commitOrigem.Substring(0, 7)))"
    $commit = if ($pai) { Rodar git commit-tree $arvore -p $pai -m $mensagem } else { Rodar git commit-tree $arvore -m $mensagem }
    Rodar git push origin "${commit}:refs/heads/$destino"
    Rodar git branch --force $destino $commit
    Write-Output "Publicado em $destino ($($commit.Substring(0, 7))). O Cloudflare começa o deploy em instantes."
} finally {
    if (Test-Path $temp) { Remove-Item -Recurse -Force $temp }
    git worktree prune
    if (Test-Path $indice) { Remove-Item -Force $indice }
}
