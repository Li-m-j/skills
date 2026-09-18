# mbai_paper_search_setup.ps1
# 作用: 首次使用 mbai_paper_search 系列的初始化向导（带交互）
# 用法:
#   .\mbai_paper_search_setup.ps1                                  # 交互式
#   .\mbai_paper_search_setup.ps1 -Mode noapi                      # 非交互，无 API 模式
#   .\mbai_paper_search_setup.ps1 -Mode api -OpenAlexKey "l1..."    # 填 OpenAlex
#   .\mbai_paper_search_setup.ps1 -Mode api -SSKey "abc..."         # 填 Semantic Scholar
#   .\mbai_paper_search_setup.ps1 -Mode api -NcbiKey "1234..."      # 填 NCBI (PubMed)
#   .\mbai_paper_search_setup.ps1 -Mode api -EuropePmcEmail "a@b.c" # 填 Europe PMC email

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [ValidateSet('api', 'noapi')]
    [string]$Mode,

    [Parameter(Mandatory = $false)]
    [string]$OpenAlexKey,

    [Parameter(Mandatory = $false)]
    [string]$SSKey,

    [Parameter(Mandatory = $false)]
    [string]$NcbiKey,

    [Parameter(Mandatory = $false)]
    [string]$EuropePmcEmail
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DataDir = Split-Path -Parent $ScriptDir
$LocalKeyFile = Join-Path $DataDir 'api_keys.local.json'
$SetKeyScript = Join-Path $ScriptDir 'Set-ApiKey.ps1'

# ── 1. 欢迎 ─────────────────────────────────────────────
Write-Host ""
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host " mbai_paper_search v0.1 - 首次设置向导" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "本 skill 提供 医学 / 生物信息学 / 人工智能 领域学术文献检索。" -ForegroundColor Gray
Write-Host "支持 OpenAlex / Semantic Scholar / PubMed / Europe PMC。" -ForegroundColor Gray
Write-Host ""

# ── 2. 选择模式 ─────────────────────────────────────────
if (-not $Mode) {
    Write-Host "==========================================================" -ForegroundColor Yellow
    Write-Host " 请选择数据源策略" -ForegroundColor Yellow
    Write-Host "==========================================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  [1] 使用 API (推荐)" -ForegroundColor Green
    Write-Host "      + OpenAlex: 50 req/s (有 key) vs 5 req/s (无 key)" -ForegroundColor Gray
    Write-Host "      + PubMed/NCBI: 10 req/s (有 key) vs 3 req/s (无 key)" -ForegroundColor Gray
    Write-Host "      + Semantic Scholar: 100 req/s (有 key) vs 共享 IP" -ForegroundColor Gray
    Write-Host "      + Europe PMC: 礼貌标识即可，无硬限流" -ForegroundColor Gray
    Write-Host "      - 申请 key:" -ForegroundColor Gray
    Write-Host "        OpenAlex:        https://openalex.org/users/sign_up" -ForegroundColor Gray
    Write-Host "        Semantic Scholar:https://www.semanticscholar.org/product/api" -ForegroundColor Gray
    Write-Host "        NCBI (PubMed):   https://www.ncbi.nlm.nih.gov/account/settings/" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  [2] 不使用 API" -ForegroundColor Yellow
    Write-Host "      + 零配置，直接用" -ForegroundColor Gray
    Write-Host "      - 限流更严，部分功能受限" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  [Q] 退出设置" -ForegroundColor Gray
    Write-Host ""

    $choice = ''
    while ($choice -notin @('1', '2', 'q', 'Q')) {
        $choice = Read-Host "  您的选择 [1=使用API / 2=不使用API / Q=退出]"
    }

    if ($choice -in @('q', 'Q')) { exit 0 }
    $Mode = if ($choice -eq '1') { 'api' } else { 'noapi' }
    Write-Host ""
    Write-Host "  已选择: $Mode" -ForegroundColor Green
}

# ── 3. noapi 模式 ─────────────────────────────────────
if ($Mode -eq 'noapi') {
    if (Test-Path -Path $LocalKeyFile -PathType Leaf) {
        $overwrite = Read-Host "  $LocalKeyFile 已存在，是否覆盖? [y/N]"
        if ($overwrite -ne 'y' -and $overwrite -ne 'Y') {
            Write-Host "  跳过" -ForegroundColor Gray; exit 0
        }
    }
    $noApiData = @{
        version = '0.1.0'; mode = 'noapi'
        providers = @{}
        note = '用户选择不使用 API。所有检索以匿名模式运行。'
        created_at = (Get-Date -Format 'yyyy-MM-dd')
    }
    $json = $noApiData | ConvertTo-Json -Depth 5
    $utf8Bom = New-Object System.Text.UTF8Encoding $true
    [System.IO.File]::WriteAllText($LocalKeyFile, $json, $utf8Bom)
    Write-Host ""
    Write-Host "  OK: 已创建 $LocalKeyFile (noapi 模式)" -ForegroundColor Green
    Write-Host ""
    exit 0
}

# ── 4. API 模式：逐项配置 ────────────────────────────
Write-Host ""
Write-Host "=========================================================" -ForegroundColor Yellow
Write-Host " 使用 API 模式" -ForegroundColor Yellow
Write-Host "=========================================================" -ForegroundColor Yellow
Write-Host ""

# 4.1 OpenAlex
if (-not $OpenAlexKey) {
    Write-Host "  [1/4] OpenAlex API key" -ForegroundColor Cyan
    Write-Host "        申请: https://openalex.org/users/sign_up" -ForegroundColor Gray
    Write-Host "        留空跳过 (限流 5 req/s)" -ForegroundColor Gray
    $input = Read-Host "        OpenAlex key (回车跳过)"
    if ($input) { $OpenAlexKey = $input }
}

# 4.2 Semantic Scholar
if (-not $SSKey) {
    Write-Host ""
    Write-Host "  [2/4] Semantic Scholar API key (可选)" -ForegroundColor Cyan
    Write-Host "        申请: https://www.semanticscholar.org/product/api" -ForegroundColor Gray
    Write-Host "        留空跳过 (共享 IP 限流)" -ForegroundColor Gray
    $input = Read-Host "        SS key (回车跳过)"
    if ($input) { $SSKey = $input }
}

# 4.3 NCBI / PubMed
if (-not $NcbiKey) {
    Write-Host ""
    Write-Host "  [3/4] NCBI API key (PubMed 加速, 推荐)" -ForegroundColor Cyan
    Write-Host "        申请: https://www.ncbi.nlm.nih.gov/account/settings/" -ForegroundColor Gray
    Write-Host "        留空跳过 (PubMed 限流降到 3 req/s)" -ForegroundColor Gray
    $input = Read-Host "        NCBI key (回车跳过)"
    if ($input) { $NcbiKey = $input }
}

# 4.4 Europe PMC
if (-not $EuropePmcEmail) {
    Write-Host ""
    Write-Host "  [4/4] Europe PMC 礼貌标识 (邮箱, 推荐)" -ForegroundColor Cyan
    Write-Host "        无需申请，直接填邮箱作为礼貌标识" -ForegroundColor Gray
    Write-Host "        留空跳过" -ForegroundColor Gray
    $input = Read-Host "        Europe PMC 邮箱 (回车跳过)"
    if ($input) { $EuropePmcEmail = $input }
}

# ── 5. 写入 local 文件 ─────────────────────────────────
Write-Host ""
Write-Host "=========================================================" -ForegroundColor Yellow
Write-Host " 写入配置" -ForegroundColor Yellow
Write-Host "=========================================================" -ForegroundColor Yellow
Write-Host ""

if (Test-Path -Path $LocalKeyFile -PathType Leaf) {
    $overwrite = Read-Host "  $LocalKeyFile 已存在，是否覆盖? [y/N]"
    if ($overwrite -ne 'y' -and $overwrite -ne 'Y') {
        Write-Host "  跳过创建。可用 Set-ApiKey.ps1 单独更新 key" -ForegroundColor Gray
        exit 0
    }
}

if ($OpenAlexKey)    { & $SetKeyScript -Provider openalex         -Key $OpenAlexKey }
if ($SSKey)          { & $SetKeyScript -Provider semantic_scholar -Key $SSKey }
if ($NcbiKey)        { & $SetKeyScript -Provider ncbi             -Key $NcbiKey }
if ($EuropePmcEmail) { & $SetKeyScript -Provider europe_pmc       -Key $EuropePmcEmail }

# ── 6. 验证 ────────────────────────────────────────────
Write-Host ""
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host " 验证 API key" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
& $SetKeyScript -Validate

# ── 7. 总结 ────────────────────────────────────────────
Write-Host ""
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host " 设置完成" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "本地配置: $LocalKeyFile" -ForegroundColor Green
Write-Host "  OpenAlex:         $(if ($OpenAlexKey)    { '已配置' } else { '未配置' })" -ForegroundColor $(if ($OpenAlexKey)    { 'Green' } else { 'Yellow' })
Write-Host "  Semantic Scholar: $(if ($SSKey)          { '已配置' } else { '未配置' })" -ForegroundColor $(if ($SSKey)          { 'Green' } else { 'Yellow' })
Write-Host "  NCBI (PubMed):    $(if ($NcbiKey)        { '已配置' } else { '未配置' })" -ForegroundColor $(if ($NcbiKey)        { 'Green' } else { 'Yellow' })
Write-Host "  Europe PMC:       $(if ($EuropePmcEmail) { '已配置' } else { '未配置' })" -ForegroundColor $(if ($EuropePmcEmail) { 'Green' } else { 'Yellow' })
Write-Host ""
Write-Host "后续操作:" -ForegroundColor Yellow
Write-Host "  查看状态:  .\Set-ApiKey.ps1 -List"
Write-Host "  验证 key:  .\Set-ApiKey.ps1 -Validate"
Write-Host "  更新 key:  .\Set-ApiKey.ps1 -Provider openalex -Key 'NEW_KEY'"
Write-Host "  切换模式:  .\mbai_paper_search_setup.ps1 -Mode noapi"
Write-Host ""
Write-Host "详细文档: $DataDir\README_API_KEYS.md" -ForegroundColor Gray
