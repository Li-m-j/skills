# Set-ApiKey.ps1 (mbai 版)
# 作用: 设置/更新/删除 API key
# 用法:
#   .\Set-ApiKey.ps1 -Provider openalex -Key "l1..."
#   .\Set-ApiKey.ps1 -Provider semantic_scholar -Key "abc..."
#   .\Set-ApiKey.ps1 -Provider ncbi -Key "1234..."
#   .\Set-ApiKey.ps1 -Provider europe_pmc -Key "your@email.com"
#   .\Set-ApiKey.ps1 -Provider openalex -EnvVar          # 改用环境变量
#   .\Set-ApiKey.ps1 -Provider ncbi -Remove              # 删除 key
#   .\Set-ApiKey.ps1 -List                               # 列出当前 key 状态
#   .\Set-ApiKey.ps1 -Validate                           # 验证 key 有效性

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [ValidateSet('openalex', 'semantic_scholar', 'ncbi', 'europe_pmc')]
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

# 4 个 provider 的环境变量名映射
$EnvNameMap = @{
    'openalex'         = 'OPENALEX_API_KEY'
    'semantic_scholar' = 'SEMANTIC_SCHOLAR_API_KEY'
    'ncbi'             = 'NCBI_API_KEY'
    'europe_pmc'       = 'EUROPE_PMC_CONTACT_EMAIL'
}

# 各 provider 的备注
$ProviderNoteMap = @{
    'openalex'         = 'OpenAlex polite pool 标识 / 加速'
    'semantic_scholar' = 'Semantic Scholar API key'
    'ncbi'             = 'NCBI E-utilities key (PubMed 加速到 10 req/s)'
    'europe_pmc'       = 'Europe PMC 礼貌标识 (邮箱)'
}

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

function Save-LocalKeys {
    param([hashtable]$Data)
    $json = $Data | ConvertTo-Json -Depth 10
    $utf8Bom = New-Object System.Text.UTF8Encoding $true
    [System.IO.File]::WriteAllText($LocalKeyFile, $json, $utf8Bom)
}

# ── List 模式 ─────────────────────────────────────────────
if ($List) {
    Write-Host "=== mbai_paper_search 当前 API key 状态 ===" -ForegroundColor Cyan
    Write-Host ""
    $local = Get-LocalKeys
    if ($local) {
        Write-Host "  本地文件: $LocalKeyFile" -ForegroundColor Green
        foreach ($p in @('openalex', 'semantic_scholar', 'ncbi', 'europe_pmc')) {
            $val = $local.providers.$p
            if ($val) {
                $shortKey = if ($val.key.Length -gt 8) { $val.key.Substring(0, 8) + '...' } else { $val.key }
                Write-Host "    $p : [$($val.source)] key=$shortKey  ($val.added_at)" -ForegroundColor Green
            } else {
                Write-Host "    $p : (未设置)" -ForegroundColor Gray
            }
        }
    } else {
        Write-Host "  本地文件: (不存在)" -ForegroundColor Gray
    }
    Write-Host ""
    Write-Host "  环境变量 (User 级别):" -ForegroundColor Cyan
    foreach ($p in @('openalex', 'semantic_scholar', 'ncbi', 'europe_pmc')) {
        $envName = $EnvNameMap[$p]
        $envVal = [Environment]::GetEnvironmentVariable($envName, 'User')
        if ($envVal) { Write-Host "    $envName : 已设置" -ForegroundColor Green }
        else { Write-Host "    $envName : (未设置)" -ForegroundColor Gray }
    }
    return
}

# ── Validate 模式 ─────────────────────────────────────────
if ($Validate) {
    Write-Host "=== 验证 mbai API key 有效性 ===" -ForegroundColor Cyan
    Write-Host ""

    # OpenAlex
    if ($Provider -in @('openalex', '')) {
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
            if ($code -eq 401) { Write-Host "  openalex: 401 Unauthorized" -ForegroundColor Red }
            elseif ($code -eq 403) { Write-Host "  openalex: 403 Forbidden" -ForegroundColor Red }
            else { Write-Host "  openalex: FAIL ($code): $($_.Exception.Message)" -ForegroundColor Red }
        }
    }

    # Semantic Scholar
    if ($Provider -in @('semantic_scholar', '')) {
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

    # PubMed / NCBI
    if ($Provider -in @('ncbi', '')) {
        $key = [Environment]::GetEnvironmentVariable('NCBI_API_KEY', 'User')
        $url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi?db=pubmed&tool=mbai_paper_search'
        if ($key) { $url += "&api_key=$key" }
        try {
            $resp = Invoke-WebRequest -Uri $url -Method GET -TimeoutSec 15 -UseBasicParsing
            if ($resp.StatusCode -eq 200) {
                Write-Host "  ncbi/PubMed: OK" -ForegroundColor Green
            } else {
                Write-Host "  ncbi/PubMed: HTTP $($resp.StatusCode)" -ForegroundColor Yellow
            }
        } catch {
            $code = $_.Exception.Response.StatusCode.value__
            if ($code -eq 429) { Write-Host "  ncbi/PubMed: 429 Rate Limited" -ForegroundColor Yellow }
            else { Write-Host "  ncbi/PubMed: FAIL ($code): $($_.Exception.Message)" -ForegroundColor Red }
        }
    }

    # Europe PMC
    if ($Provider -in @('europe_pmc', '')) {
        $url = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=test&format=json&pageSize=1'
        try {
            $resp = Invoke-RestMethod -Uri $url -Method GET -TimeoutSec 15
            if ($resp.hitCount -ne $null) {
                Write-Host "  europe_pmc: OK (hitCount=$($resp.hitCount))" -ForegroundColor Green
            } else {
                Write-Host "  europe_pmc: UNEXPECTED RESPONSE" -ForegroundColor Yellow
            }
        } catch {
            $code = $_.Exception.Response.StatusCode.value__
            Write-Host "  europe_pmc: FAIL ($code): $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    return
}

# ── 需要 Provider 的操作 ──────────────────────────────
if (-not $Provider) {
    Write-Error "需要指定 -Provider (openalex | semantic_scholar | ncbi | europe_pmc)。用 -List 查看当前状态。"
    exit 1
}

$envName = $EnvNameMap[$Provider]

# ── Remove 模式 ────────────────────────────────────────
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
    $envVal = [Environment]::GetEnvironmentVariable($envName, 'User')
    if ($envVal) {
        [Environment]::SetEnvironmentVariable($envName, $null, 'User')
        Write-Host "  OK: 已删除 User 级别环境变量 $envName" -ForegroundColor Green
    } else {
        Write-Host "  User 级别环境变量 $envName 未设置，跳过" -ForegroundColor Gray
    }
    return
}

# ── EnvVar 模式 ───────────────────────────────────────
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
    $envVal = [Environment]::GetEnvironmentVariable($envName, 'User')
    if ($envVal) {
        Write-Host "  OK: $envName 已设置" -ForegroundColor Green
    } else {
        Write-Host "  WARN: $envName 未设置。请用以下命令设置:" -ForegroundColor Yellow
        Write-Host "    [Environment]::SetEnvironmentVariable('$envName', 'YOUR_KEY', 'User')"
    }
    return
}

# ── Set 模式 ──────────────────────────────────────────
if (-not $Key) {
    Write-Error "需要 -Key 参数。或用 -EnvVar / -Remove / -List / -Validate"
    exit 1
}

if ($Key -match 'YOUR_.*_KEY_HERE|REPLACE_WITH_') {
    Write-Error "key 是占位符，请提供真实 key"
    exit 1
}

Write-Host "=== 设置 $Provider key ===" -ForegroundColor Cyan
$local = Get-LocalKeys
if (-not $local) {
    $local = @{ version = '0.1.0'; providers = @{} }
}
if (-not $local.providers) { $local.providers = @{} }

$providerData = @{
    key      = $Key
    added_at = (Get-Date -Format 'yyyy-MM-dd')
    source   = 'local'
    note     = $ProviderNoteMap[$Provider]
}

$local.providers | Add-Member -NotePropertyName $Provider -NotePropertyValue $providerData -Force
Save-LocalKeys -Data $local
Write-Host "  OK: $Provider key 已写入 $LocalKeyFile" -ForegroundColor Green
$shortKey = if ($Key.Length -gt 8) { $Key.Substring(0, 8) + '...' } else { $Key }
Write-Host "  Key 前 8 位: $shortKey" -ForegroundColor Gray
Write-Host ""
Write-Host "  验证一下 (可选):" -ForegroundColor Yellow
Write-Host "    .\Set-ApiKey.ps1 -Validate -Provider $Provider"
