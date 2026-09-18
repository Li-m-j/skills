# Set-ApiKey.ps1
# 作用: 设置/更新/删除 API key
# 用法:
#   .\Set-ApiKey.ps1 -Provider openalex -Key "YOUR_OPENALEX_KEY_HERE"   # 注意：不要把真实 key 写进本文件的注释/提交到 git
#   .\Set-ApiKey.ps1 -Provider openalex -EnvVar          # 改用环境变量
#   .\Set-ApiKey.ps1 -Provider openalex -Remove         # 删除 key
#   .\Set-ApiKey.ps1 -List                              # 列出当前 key 状态
#   .\Set-ApiKey.ps1 -Validate                          # 验证 key 有效性

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [ValidateSet('openalex', 'semantic_scholar')]
    [string]$Provider,

    [Parameter(Mandatory = $false)]
    [string]$Key,

    [Parameter(Mandatory = $false)]
    [switch]$EnvVar,

    [Parameter(Mandatory = $false)]
    [switch]$Remove,

    [Parameter(Mandatory = $false)]
    [switch]$List,

    [Parameter(Mandatory = $false)]
    [switch]$Validate
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DataDir = Split-Path -Parent $ScriptDir
$LocalKeyFile = Join-Path $DataDir 'api_keys.local.json'
$TemplateKeyFile = Join-Path $DataDir 'api_keys.template.json'

# Helper: 读 local 文件（不存在返回空 hashtable）
function Get-LocalKeys {
    if (Test-Path -Path $LocalKeyFile -PathType Leaf) {
        try {
            $content = Get-Content -Raw -Path $LocalKeyFile -Encoding UTF8
            if ([string]::IsNullOrWhiteSpace($content)) { return @{ providers = @{} } }
            return $content | ConvertFrom-Json
        } catch {
            Write-Warning "local 文件解析失败: $LocalKeyFile"
            return $null
        }
    }
    return $null
}

# Helper: 写 local 文件
function Save-LocalKeys {
    param([hashtable]$Data)
    $json = $Data | ConvertTo-Json -Depth 10
    $utf8Bom = New-Object System.Text.UTF8Encoding $true
    [System.IO.File]::WriteAllText($LocalKeyFile, $json, $utf8Bom)
}

# List 模式
if ($List) {
    Write-Host "=== 当前 API key 状态 ===" -ForegroundColor Cyan
    Write-Host ""
    $local = Get-LocalKeys
    if ($local) {
        Write-Host "  本地文件: $LocalKeyFile" -ForegroundColor Green
        if ($local.providers.openalex) {
            $status = $local.providers.openalex.key
            $source = 'local'
            Write-Host "    openalex: [$source] key=$status"
        } else {
            Write-Host "    openalex: (未设置)" -ForegroundColor Gray
        }
        if ($local.providers.semantic_scholar) {
            $status = $local.providers.semantic_scholar.key
            $source = 'local'
            Write-Host "    semantic_scholar: [$source] key=$status"
        } else {
            Write-Host "    semantic_scholar: (未设置)" -ForegroundColor Gray
        }
    } else {
        Write-Host "  本地文件: (不存在)" -ForegroundColor Gray
    }
    Write-Host ""
    Write-Host "  环境变量:"
    $envOA = [Environment]::GetEnvironmentVariable('OPENALEX_API_KEY', 'User')
    $envSS = [Environment]::GetEnvironmentVariable('SEMANTIC_SCHOLAR_API_KEY', 'User')
    if ($envOA) { Write-Host "    OPENALEX_API_KEY: 已设置" -ForegroundColor Green }
    else { Write-Host "    OPENALEX_API_KEY: (未设置)" -ForegroundColor Gray }
    if ($envSS) { Write-Host "    SEMANTIC_SCHOLAR_API_KEY: 已设置" -ForegroundColor Green }
    else { Write-Host "    SEMANTIC_SCHOLAR_API_KEY: (未设置)" -ForegroundColor Gray }
    return
}

# Validate 模式
if ($Validate) {
    Write-Host "=== 验证 API key 有效性 ===" -ForegroundColor Cyan
    Write-Host ""

    if ($Provider -eq 'openalex' -or !$Provider) {
        $key = [Environment]::GetEnvironmentVariable('OPENALEX_API_KEY', 'User')
        if (-not $key) { $key = 'no-key' }
        $url = "https://api.openalex.org/works?per_page=1&api_key=$key"
        try {
            $resp = Invoke-RestMethod -Uri $url -Method GET -TimeoutSec 15
            if ($resp.meta) {
                Write-Host "  openalex: OK (count=$($resp.meta.count))" -ForegroundColor Green
            } else {
                Write-Host "  openalex: UNEXPECTED RESPONSE" -ForegroundColor Yellow
            }
        } catch {
            $code = $_.Exception.Response.StatusCode.value__
            if ($code -eq 401) { Write-Host "  openalex: 401 Unauthorized (key 无效)" -ForegroundColor Red }
            elseif ($code -eq 403) { Write-Host "  openalex: 403 Forbidden" -ForegroundColor Red }
            else { Write-Host "  openalex: FAIL ($code): $($_.Exception.Message)" -ForegroundColor Red }
        }
    }

    if ($Provider -eq 'semantic_scholar' -or !$Provider) {
        $key = [Environment]::GetEnvironmentVariable('SEMANTIC_SCHOLAR_API_KEY', 'User')
        $headers = @{}
        if ($key) { $headers['x-api-key'] = $key }
        $url = 'https://api.semanticscholar.org/graph/v1/paper/search?query=test&limit=1'
        try {
            $resp = Invoke-RestMethod -Uri $url -Method GET -TimeoutSec 15 -Headers $headers
            if ($resp.data) {
                Write-Host "  semantic_scholar: OK (total=$($resp.total))" -ForegroundColor Green
            } else {
                Write-Host "  semantic_scholar: UNEXPECTED RESPONSE" -ForegroundColor Yellow
            }
        } catch {
            $code = $_.Exception.Response.StatusCode.value__
            if ($code -eq 401) { Write-Host "  semantic_scholar: 401 Unauthorized" -ForegroundColor Red }
            elseif ($code -eq 429) { Write-Host "  semantic_scholar: 429 Rate Limited" -ForegroundColor Yellow }
            else { Write-Host "  semantic_scholar: FAIL ($code): $($_.Exception.Message)" -ForegroundColor Red }
        }
    }
    return
}

# 以下操作需要 Provider
if (-not $Provider) {
    Write-Error "需要指定 -Provider (openalex 或 semantic_scholar)。用 -List 查看当前状态。"
    exit 1
}

# Remove 模式
if ($Remove) {
    Write-Host "=== 删除 $Provider key ===" -ForegroundColor Cyan
    $local = Get-LocalKeys
    if ($local -and $local.providers.$Provider) {
        $local.providers.PSObject.Properties.Remove($Provider)
        Save-LocalKeys -Data $local
        Write-Host "  OK: 已从 local 文件删除" -ForegroundColor Green
    } else {
        Write-Host "  local 文件中无 $Provider key，跳过" -ForegroundColor Gray
    }
    $envName = if ($Provider -eq 'openalex') { 'OPENALEX_API_KEY' } else { 'SEMANTIC_SCHOLAR_API_KEY' }
    $envVal = [Environment]::GetEnvironmentVariable($envName, 'User')
    if ($envVal) {
        [Environment]::SetEnvironmentVariable($envName, $null, 'User')
        Write-Host "  OK: 已删除 User 级别环境变量 $envName" -ForegroundColor Green
    } else {
        Write-Host "  User 级别环境变量 $envName 未设置，跳过" -ForegroundColor Gray
    }
    return
}

# EnvVar 模式
if ($EnvVar) {
    Write-Host "=== 切到环境变量模式（删除 local key）===" -ForegroundColor Cyan
    $local = Get-LocalKeys
    if ($local -and $local.providers.$Provider) {
        $local.providers.PSObject.Properties.Remove($Provider)
        Save-LocalKeys -Data $local
        Write-Host "  OK: 已从 local 文件删除 $Provider" -ForegroundColor Green
    } else {
        Write-Host "  local 文件中无 $Provider key" -ForegroundColor Gray
    }
    $envName = if ($Provider -eq 'openalex') { 'OPENALEX_API_KEY' } else { 'SEMANTIC_SCHOLAR_API_KEY' }
    $envVal = [Environment]::GetEnvironmentVariable($envName, 'User')
    if ($envVal) {
        Write-Host "  OK: $envName 已设置 ($($envVal.Substring(0, [Math]::Min(8, $envVal.Length)))...)" -ForegroundColor Green
    } else {
        Write-Host "  WARN: $envName 未设置。请用以下命令设置:" -ForegroundColor Yellow
        Write-Host "    [Environment]::SetEnvironmentVariable('$envName', 'YOUR_KEY', 'User')"
    }
    return
}

# Set 模式（需要 -Key）
if (-not $Key) {
    Write-Error "需要 -Key 参数。或用 -EnvVar / -Remove / -List / -Validate"
    exit 1
}

if ($Key -match 'YOUR_.*_KEY_HERE') {
    Write-Error "key 是占位符，请提供真实 key"
    exit 1
}

Write-Host "=== 设置 $Provider key ===" -ForegroundColor Cyan
$local = Get-LocalKeys
if (-not $local) {
    $local = @{ version = '0.2.3'; providers = @{} }
}
if (-not $local.providers) { $local.providers = @{} }

# 用 hashtable 重新构造（避免 PSCustomObject 的限制）
$providerData = @{
    key       = $Key
    added_at  = (Get-Date -Format 'yyyy-MM-dd')
    source    = 'local'
    note      = if ($Provider -eq 'openalex') { 'OpenAlex polite pool 标识' } else { 'Semantic Scholar API key' }
}

# ConvertTo-Json 处理 PSCustomObject 嵌套
$local.providers | Add-Member -NotePropertyName $Provider -NotePropertyValue $providerData -Force

# 写文件
Save-LocalKeys -Data $local
Write-Host "  OK: $Provider key 已写入 $LocalKeyFile" -ForegroundColor Green
Write-Host "  Key 前 8 位: $($Key.Substring(0, [Math]::Min(8, $Key.Length)))..." -ForegroundColor Gray
Write-Host ""
Write-Host "  验证一下 (可选):" -ForegroundColor Yellow
Write-Host "    .\Set-ApiKey.ps1 -Validate"
