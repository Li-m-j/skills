# se_openalex_to_md.ps1 (se_paper_search v0.1.0)
# 将 OpenAlex API 返回的 JSON 转换为统计/经济学文献检索 .md 名录。
# broad 模式：宽召回 + abstract 二次方向过滤。
# 派生自 qm_openalex_to_md.ps1；作者: Mavis
# 日期: 2026-09-18

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$InputJsonFile,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$OutputMdFile,

    [Parameter(Mandatory = $false)]
    [string]$Query = "N/A",

    [Parameter(Mandatory = $false)]
    [string]$TopicName = "N/A",

    [Parameter(Mandatory = $false)]
    [ValidateSet("fine", "broad")]
    [string]$Mode = "fine",

    [Parameter(Mandatory = $false)]
    [int]$Count = 0,

    [Parameter(Mandatory = $false)]
    [switch]$Quiet,

    # broad 模式参数
    [Parameter(Mandatory = $false)]
    [string]$BroadConceptPattern = "econometric|causal[ ]inference|treatment[ ]effect|statistical[ ]inference",

    [Parameter(Mandatory = $false)]
    [ValidateRange(0, 10)]
    [int]$BroadMinMatch = 1,

    [Parameter(Mandatory = $false)]
    [switch]$BroadNoFilter
)

$ErrorActionPreference = 'Stop'

# 1. 校验输入
if (-not (Test-Path -Path $InputJsonFile -PathType Leaf)) {
    Write-Error "JSON 文件不存在: $InputJsonFile"
    exit 1
}

# 2. 读 JSON
if (-not $Quiet) { Write-Host "[1/6] 读取 JSON: $InputJsonFile" -ForegroundColor Cyan }
$rawJson = Get-Content -Raw -Path $InputJsonFile -Encoding UTF8
try {
    $json = $rawJson | ConvertFrom-Json
} catch {
    # PS 5.1 的 ConvertFrom-Json 不允许仅大小写不同的重复键，
    # 而 OpenAlex abstract_inverted_index 可能同时含 "To"/"to" 等词形。
    # 兜底：剥掉 abstract_inverted_index 后重试（摘要将降级为 N/A）。
    $stripped = [regex]::Replace($rawJson, '"abstract_inverted_index"\s*:\s*\{[^{}]*\}', '"abstract_inverted_index": null')
    $json = $stripped | ConvertFrom-Json
    if (-not $Quiet) { Write-Warning "JSON 含大小写敏感重复键（abstract_inverted_index），已剥离摘要字段后重试；本次输出的摘要均为 N/A" }
}

if ($json -is [array]) {
    $json = [PSCustomObject]@{ results = $json }
}

if (-not $json.results) {
    Write-Warning "JSON 中无 results 字段"
    exit 1
}

$allResults = $json.results
if (-not $Quiet) { Write-Host "    JSON 原始命中: $($allResults.Count) 篇" -ForegroundColor Gray }

# 3. abstract 还原函数
function Restore-Abstract {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $false)]
        $InvertedIndex
    )

    if (-not $InvertedIndex) { return $null }

    $tokens = @()
    foreach ($prop in $InvertedIndex.PSObject.Properties) {
        foreach ($pos in $prop.Value) {
            $tokens += [PSCustomObject]@{
                Pos  = $pos
                Word = $prop.Name
            }
        }
    }
    $sorted = $tokens | Sort-Object Pos
    return ($sorted | ForEach-Object { $_.Word }) -join ' '
}

# 4. broad 模式二次过滤函数（方案 H 核心）
function Test-BroadRelevance {
    [CmdletBinding()]
    [OutputType([bool])]
    param(
        [Parameter(Mandatory = $true)]
        $Paper,

        [Parameter(Mandatory = $true)]
        [string]$Pattern,

        [Parameter(Mandatory = $true)]
        [int]$MinMatch
    )

    $abstract = Restore-Abstract $Paper.abstract_inverted_index
    if (-not $abstract) { return $true }

    $matches = [regex]::Matches($abstract, $Pattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    return $matches.Count -ge $MinMatch
}

# 5. 期刊档位速查表（ISSN → 档；与 se_journal_tiers.json 口径一致，不写 IF 数值以免过时）
$journalTier = @{
    "0012-9682" = "Tier 1 · Top（Econometrica）"
    "0002-8282" = "Tier 1 · Top（American Economic Review）"
    "0033-5533" = "Tier 1 · Top（Quarterly Journal of Economics）"
    "0022-3808" = "Tier 1 · Top（Journal of Political Economy）"
    "0034-6527" = "Tier 1 · Top（Review of Economic Studies）"
    "0090-5364" = "Tier 1 · Top（Annals of Statistics）"
    "0162-1459" = "Tier 1 · Top（JASA）"
    "0006-3444" = "Tier 1 · Top（Biometrika）"
    "1369-7412" = "Tier 1 · Top（JRSS-B）"
    "0022-1082" = "Tier 1 · Top（Journal of Finance）"
    "0304-405X" = "Tier 1 · Top（Journal of Financial Economics）"
    "0893-9454" = "Tier 1 · Top（Review of Financial Studies）"
    "0577-9154" = "Tier 1 · Top（经济研究）"
    "0304-4076" = "Tier 2（Journal of Econometrics）"
    "0272-3182" = "Tier 2（Journal of Business & Economic Statistics）"
    "0883-4237" = "Tier 2（Statistical Science）"
    "0266-4666" = "Tier 2（Econometric Theory）"
    "1368-4221" = "Tier 2（Econometrics Journal）"
    "1350-7265" = "Tier 2（Bernoulli）"
    "1532-4435" = "Tier 2（JMLR）"
    "0034-6535" = "Tier 2（Review of Economics and Statistics）"
}

# 6. broad 模式二次过滤
$results = $allResults
if ($Mode -eq 'broad') {
    if (-not $Quiet) { Write-Host "[2/6] Broad 模式：应用二次过滤" -ForegroundColor Yellow }

    if ($BroadNoFilter) {
        if (-not $Quiet) { Write-Host "    (跳过二次过滤)" -ForegroundColor Gray }
    } else {
        $beforeCount = $results.Count
        $results = @($results | Where-Object {
            Test-BroadRelevance -Paper $_ -Pattern $BroadConceptPattern -MinMatch $BroadMinMatch
        })
        $afterCount = $results.Count
        $filtered = $beforeCount - $afterCount
        if (-not $Quiet) {
            Write-Host "    过滤前: $beforeCount 篇" -ForegroundColor Gray
            Write-Host "    过滤后: $afterCount 篇 (过滤掉 $filtered 篇)" -ForegroundColor Gray
        }
    }
}

# 7. 应用 Count 限制
if ($Count -gt 0 -and $Count -lt $results.Count) {
    $results = $results | Select-Object -First $Count
}
if (-not $Quiet) { Write-Host "[3/6] 最终输出: $($results.Count) 篇" -ForegroundColor Cyan }

# 8. 拼 Markdown
if (-not $Quiet) { Write-Host "[4/6] 拼装 Markdown" -ForegroundColor Cyan }
$sb = New-Object System.Text.StringBuilder

[void]$sb.AppendLine("# 文献检索结果 ($Mode 模式 · se_paper_search v0.1.0)")
[void]$sb.AppendLine("")
[void]$sb.AppendLine("查询: $Query")
[void]$sb.AppendLine("研究方向: $TopicName")
[void]$sb.AppendLine("时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm')")
[void]$sb.AppendLine("数据源: OpenAlex API (带 key)")
[void]$sb.AppendLine("模式: $Mode")
if ($Mode -eq 'fine') {
    [void]$sb.AppendLine("搜索策略: title.search + concepts.id")
} else {
    [void]$sb.AppendLine("搜索策略: 宽召回 + abstract 二次过滤")
    [void]$sb.AppendLine("二次过滤正则: $BroadConceptPattern")
    [void]$sb.AppendLine("最少命中数: $BroadMinMatch")
}
[void]$sb.AppendLine("")

# 速览表
[void]$sb.AppendLine("## 速览 ($($results.Count) 篇)")
[void]$sb.AppendLine("")
[void]$sb.AppendLine("| # | 标题 | 作者 | 年份 | DOI |")
[void]$sb.AppendLine("|---|------|------|------|-----|")

for ($i = 0; $i -lt $results.Count; $i++) {
    $p = $results[$i]
    $num = $i + 1
    $titleEsc = $p.title -replace '\|', '\|'
    $authors = 'N/A'
    if ($p.authorships) {
        $names = @($p.authorships | ForEach-Object { $_.author.display_name })
        $first3 = $names | Select-Object -First 3
        if ($first3) {
            $authors = ($first3 -join ', ')
            if ($names.Count -gt 3) { $authors = $authors + ', et al.' }
        }
    }
    $year = $p.publication_year
    $doi = 'N/A'
    if ($p.doi) { $doi = $p.doi -replace 'https://doi.org/', '' }
    $anchor = "title-$num"
    if ($doi -ne 'N/A') {
        [void]$sb.AppendLine("| $num | [$titleEsc](#$anchor) | $authors | $year | [$doi](https://doi.org/$doi) |")
    } else {
        [void]$sb.AppendLine("| $num | [$titleEsc](#$anchor) | $authors | $year | N/A |")
    }
}

[void]$sb.AppendLine("")

# 详细条目
[void]$sb.AppendLine("## 详细条目")
[void]$sb.AppendLine("")

for ($i = 0; $i -lt $results.Count; $i++) {
    $p = $results[$i]
    $num = $i + 1
    $title = $p.title
    $authorsFull = 'N/A'
    if ($p.authorships) {
        $authorsFull = ($p.authorships | ForEach-Object { $_.author.display_name }) -join ', '
    }
    $year = $p.publication_year
    $doi = 'N/A'
    if ($p.doi) { $doi = $p.doi -replace 'https://doi.org/', '' }
    $venue = 'N/A'
    if ($p.primary_location.source.display_name) { $venue = $p.primary_location.source.display_name }
    $issn = $p.primary_location.source.issn_l
    $tier = 'N/A'
    if ($issn -and $journalTier.ContainsKey($issn)) { $tier = $journalTier[$issn] }
    $cite = $p.cited_by_count
    $abstract = Restore-Abstract $p.abstract_inverted_index
    if (-not $abstract) { $abstract = 'N/A (OpenAlex 未提供)' }
    $anchor = "title-$num"

    [void]$sb.AppendLine("### # $num <a id=`"$anchor`"></a> $title")
    [void]$sb.AppendLine("")
    [void]$sb.AppendLine("- 作者: $authorsFull")
    [void]$sb.AppendLine("- 年份: $year")
    [void]$sb.AppendLine("- 期刊: $venue")
    [void]$sb.AppendLine("- 档位: $tier")
    [void]$sb.AppendLine("- 被引: $cite")
    if ($doi -ne 'N/A') {
        [void]$sb.AppendLine("- DOI: [$doi](https://doi.org/$doi)")
    } else {
        [void]$sb.AppendLine("- DOI: N/A")
    }
    [void]$sb.AppendLine("- 摘要: $abstract")
    [void]$sb.AppendLine("")

    $firstAuthorSurname = 'N/A'
    if ($p.authorships -and $p.authorships[0].author.display_name) {
        $parts = $p.authorships[0].author.display_name -split ' '
        $firstAuthorSurname = $parts[-1]
    }

    [void]$sb.AppendLine("#### 引用格式")
    [void]$sb.AppendLine("")
    [void]$sb.AppendLine('<details>')
    [void]$sb.AppendLine('<summary></summary>')
    [void]$sb.AppendLine("")
    [void]$sb.AppendLine('```bibtex')
    [void]$sb.AppendLine("@article{$firstAuthorSurname$year, title = {$title}, journal = {$venue}, year = {$year}}")
    [void]$sb.AppendLine('```')
    [void]$sb.AppendLine('</details>')
    [void]$sb.AppendLine("")
    [void]$sb.AppendLine("---")
    [void]$sb.AppendLine("")
}

# 9. 落盘
$outputDir = Split-Path -Parent $OutputMdFile
if ($outputDir -and -not (Test-Path -Path $outputDir -PathType Container)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

$sb.ToString() | Out-File -FilePath $OutputMdFile -Encoding UTF8 -Force

if (-not $Quiet) {
    Write-Host "[5/6] 写入: $OutputMdFile" -ForegroundColor Green
    Write-Host "[6/6] Done. Papers=$($results.Count)" -ForegroundColor Green
}