# qm_paper_search_setup.ps1
# 作用: 首次使用本 skill 时的初始化向导（带交互）
# 用法:
#   .\qm_paper_search_setup.ps1                              # 交互式
#   .\qm_paper_search_setup.ps1 -Mode api -OpenAlexKey "l1..." # 非交互，API 模式
#   .\qm_paper_search_setup.ps1 -Mode noapi                  # 非交互，无 API 模式
#   .\qm_paper_search_setup.ps1 -Mode api -SSKey "abc..."     # 完整 API 配置

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [ValidateSet('api', 'noapi')]
    [string]$Mode,

    [Parameter(Mandatory = $false)]
    [string]$OpenAlexKey,

    [Parameter(Mandatory = $false)]
    [string]$SSKey
)

$ErrorActionPreference = 'Stop'

# v0.3.0: 优先尝试 _lib_paths.ps1 (env var + 相对路径解析)，
# 失败时回退到原相对路径逻辑。
$LibPathsPath = Join-Path -Path $PSScriptRoot -ChildPath "_lib_paths.ps1"
if (Test-Path -Path $LibPathsPath -PathType Leaf) {
    try {
        . $LibPathsPath
        $DataDir = Resolve-SharedDataDir
    } catch {
        # Helper 加载失败，回退
        $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
        $DataDir = Split-Path -Parent $ScriptDir
    }
} else {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $DataDir = Split-Path -Parent $ScriptDir
}

$LocalKeyFile = Join-Path $DataDir 'api_keys.local.json'
$TemplateKeyFile = Join-Path $DataDir 'api_keys.template.json'
$SetKeyScript = Join-Path $PSScriptRoot 'Set-ApiKey.ps1'

# ── 1. 欢迎与说明 ─────────────────────────────────────────────
Write-Host ""
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host " qm_paper_search skill v0.2.3 - 首次设置向导" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "本 skill 提供化学文献检索功能，支持 OpenAlex 和 Semantic Scholar API。" -ForegroundColor Gray
Write-Host "首次使用需要选择一个数据源策略。" -ForegroundColor Gray
Write-Host ""

# ── 2. 选择数据源策略（API 或 noapi）───────────────────────────────
if (-not $Mode) {
    Write-Host "==========================================================" -ForegroundColor Yellow
    Write-Host " 请选择数据源策略" -ForegroundColor Yellow
    Write-Host "==========================================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  [1] 使用 API  (推荐)" -ForegroundColor Green
    Write-Host "      + OpenAlex: 50 req/s (有 key) vs 5 req/s (无 key)" -ForegroundColor Gray
    Write-Host "      + Semantic Scholar: 100 req/min (有 key) vs 共享 IP 限流" -ForegroundColor Gray
    Write-Host "      + 检索更快，能跑引用图谱（references + citations）" -ForegroundColor Gray
    Write-Host "      - 需要去 https://openalex.org/users/sign_up 申请免费 key" -ForegroundColor Gray
    Write-Host "      - 和 https://www.semanticscholar.org/product/api 申请 SS key" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  [2] 不使用 API" -ForegroundColor Yellow
    Write-Host "      + 不用申请任何 key，零配置" -ForegroundColor Gray
    Write-Host "      - OpenAlex 限流降到 5 req/s（每次检索 sleep 几秒）" -ForegroundColor Gray
    Write-Host "      - Semantic Scholar 共享 IP 100 req/min（多人共用容易 429）" -ForegroundColor Gray
    Write-Host "      - 不能跑引用图谱（references + citations 需 5-10 req/篇）" -ForegroundColor Gray
    Write-Host "      - 部分功能受限但基本检索仍可用" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  [Q] 退出设置" -ForegroundColor Gray
    Write-Host ""

    $choice = ''
    while ($choice -notin @('1', '2', 'q', 'Q')) {
        $choice = Read-Host "  您的选择 [1=使用API / 2=不使用API / Q=退出]"
    }

    if ($choice -in @('q', 'Q')) {
        Write-Host "  退出设置" -ForegroundColor Gray
        exit 0
    }

    $Mode = if ($choice -eq '1') { 'api' } else { 'noapi' }
    Write-Host ""
    Write-Host "  已选择: $Mode" -ForegroundColor Green
}

# ── 3. noapi 模式：跳过 key 配置 ─────────────────────────────────
if ($Mode -eq 'noapi') {
    Write-Host ""
    Write-Host "=========================================================" -ForegroundColor Yellow
    Write-Host " 不使用 API 模式" -ForegroundColor Yellow
    Write-Host "=========================================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  将创建空的 api_keys.local.json（标记为 noapi 模式）" -ForegroundColor Gray
    Write-Host "  OpenAlex 默认 5 req/s，Semantic Scholar 共享 IP" -ForegroundColor Gray
    Write-Host "  实际使用可能遇到：检索慢、429 限流、部分功能受限" -ForegroundColor Gray
    Write-Host ""

    if (Test-Path -Path $LocalKeyFile -PathType Leaf) {
        Write-Host "  注意: $LocalKeyFile 已存在" -ForegroundColor Yellow
        $overwrite = Read-Host "  是否覆盖? [y/N]"
        if ($overwrite -ne 'y' -and $overwrite -ne 'Y') {
            Write-Host "  跳过创建" -ForegroundColor Gray
            exit 0
        }
    }

    $noApiData = @{
        version = '0.2.3'
        mode = 'noapi'
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
    Write-Host "==========================================================" -ForegroundColor Cyan
    Write-Host " 设置完成" -ForegroundColor Cyan
    Write-Host "==========================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "后续操作:" -ForegroundColor Yellow
    Write-Host "  切换到 API 模式:    .\qm_paper_search_setup.ps1 -Mode api -OpenAlexKey 'YOUR_KEY'"
    Write-Host "  查看 key 状态:      .\Set-ApiKey.ps1 -List"
    Write-Host "  开始检索:           .\qm_openalex_to_md.ps1 -InputJsonFile 'data\xxx.json' -OutputMdFile 'papers\out.md' -Mode fine"
    exit 0
}

# ── 4. API 模式：配置 key ─────────────────────────────────────
Write-Host ""
Write-Host "=========================================================" -ForegroundColor Yellow
Write-Host " 使用 API 模式" -ForegroundColor Yellow
Write-Host "=========================================================" -ForegroundColor Yellow
Write-Host ""

# 4.1 OpenAlex key
if (-not $OpenAlexKey) {
    Write-Host "  [1/2] OpenAlex API key" -ForegroundColor Cyan
    Write-Host "        免费申请: https://openalex.org/users/sign_up" -ForegroundColor Gray
    Write-Host "        留空跳过（仍可工作，限流降到 5 req/s）" -ForegroundColor Gray
    $input = Read-Host "        OpenAlex key (直接回车跳过)"
    if ($input) { $OpenAlexKey = $input }
}

# 4.2 SS key
if (-not $SSKey) {
    Write-Host ""
    Write-Host "  [2/2] Semantic Scholar API key (可选)" -ForegroundColor Cyan
    Write-Host "        免费申请: https://www.semanticscholar.org/product/api" -ForegroundColor Gray
    Write-Host "        留空跳过（仍可工作，限流降到共享 IP）" -ForegroundColor Gray
    $input = Read-Host "        SS key (直接回车跳过)"
    if ($input) { $SSKey = $input }
}

# ── 5. 创建 local 文件 ─────────────────────────────────────────
Write-Host ""
Write-Host "=========================================================" -ForegroundColor Yellow
Write-Host " 写入配置" -ForegroundColor Yellow
Write-Host "=========================================================" -ForegroundColor Yellow
Write-Host ""

if (Test-Path -Path $LocalKeyFile -PathType Leaf) {
    Write-Host "  注意: $LocalKeyFile 已存在" -ForegroundColor Yellow
    $overwrite = Read-Host "  是否覆盖? [y/N]"
    if ($overwrite -ne 'y' -and $overwrite -ne 'Y') {
        Write-Host "  跳过创建。可用 Set-ApiKey.ps1 单独更新 key" -ForegroundColor Gray
        exit 0
    }
}

# 用 Set-ApiKey.ps1 设置（确保逻辑一致）
if ($OpenAlexKey) {
    Write-Host "  设置 OpenAlex key..." -ForegroundColor Cyan
    & $SetKeyScript -Provider openalex -Key $OpenAlexKey
}

if ($SSKey) {
    Write-Host "  设置 Semantic Scholar key..." -ForegroundColor Cyan
    & $SetKeyScript -Provider semantic_scholar -Key $SSKey
}

# ── 6. 验证 ────────────────────────────────────────────────────
Write-Host ""
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host " 验证 API key" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
& $SetKeyScript -Validate

# ── 7. 总结 ────────────────────────────────────────────────────
Write-Host ""
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host " 设置完成" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "本地配置: $LocalKeyFile" -ForegroundColor Green
Write-Host "  OpenAlex: $(if ($OpenAlexKey) { '已配置' } else { '未配置（默认无 key 模式）' })" -ForegroundColor $(if ($OpenAlexKey) { 'Green' } else { 'Yellow' })
Write-Host "  Semantic Scholar: $(if ($SSKey) { '已配置' } else { '未配置' })" -ForegroundColor $(if ($SSKey) { 'Green' } else { 'Yellow' })
Write-Host ""
Write-Host "后续操作:" -ForegroundColor Yellow
Write-Host "  查看状态:  .\Set-ApiKey.ps1 -List"
Write-Host "  验证 key:   .\Set-ApiKey.ps1 -Validate"
Write-Host "  更新 key:   .\Set-ApiKey.ps1 -Provider openalex -Key 'NEW_KEY'"
Write-Host "  切换模式:   .\qm_paper_search_setup.ps1 -Mode noapi  (或 -Mode api -OpenAlexKey 'xxx')"
Write-Host ""
Write-Host "详细文档: $DataDir\README_API_KEYS.md" -ForegroundColor Gray
