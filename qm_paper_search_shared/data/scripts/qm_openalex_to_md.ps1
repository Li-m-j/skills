# qm_openalex_to_md.ps1 (v0.2.2)
# 将 OpenAlex API 返回的 JSON 转换为化学文献检索 .md 名录。
# v0.2.2 新增：方案 H 宽召回 + abstract 二次过滤（broad 模式）
# 作者: Mavis (qm_paper_search skill v0.2.2)
# 日期: 2026-09-08

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

    # v0.2.2 broad 模式参数
    [Parameter(Mandatory = $false)]
    [string]$BroadConceptPattern = "biocatalysis|enzymatic[ ]catalysis|enzyme[ ]catalysis",

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
$json = Get-Content -Raw -Path $InputJsonFile -Encoding UTF8 | ConvertFrom-Json

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

# 5. 期刊 IF 速查表
$journalIf = @{
    "0002-7863" = 14.4
    "1433-7851" = 16.1
    "2451-9294" = 19.1
    "0009-2665" = 51.4
    "0001-4842" = 16.4
    "1755-4330" = 24.9
    "2520-1158" = 20.8
    "2731-0582" = 17.5
    "2397-3358" = 38.1
    "0306-0012" = 40.4
    "0010-8545" = 20.6
    "2155-5435" = 11.3
    "0935-9648" = 27.4
    "1616-301X" = 18.5
    "1614-6832" = 24.4
    "2198-3844" = 14.3
    "1754-5692" = 32.4
    "0013-936X" = 10.8
    "1936-0851" = 15.8
    "2041-6539" = 9.6
    "1364-548X" = 4.2
    "2041-1723" = 16.6
    "0006-3592" = 3.2
    "2059-3635" = 40.8
    "1463-9262" = 9.8
    "2639-4979" = 8.0
    "1944-8244" = 9.5
    "1932-7447" = 4.0
    "2095-4956" = 14.0
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

[void]$sb.AppendLine("# 文献检索结果 ($Mode 模式 · v0.2.2)")
[void]$sb.AppendLine("")
[void]$sb.AppendLine("查询: $Query")
[void]$sb.AppendLine("研究方向: $TopicName")
[void]$sb.AppendLine("时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm')")
[void]$sb.AppendLine("数据源: OpenAlex API (带 key)")
[void]$sb.AppendLine("模式: $Mode")
if ($Mode -eq 'fine') {
    [void]$sb.AppendLine("搜索策略: v0.2.1 (title.search + concepts.id)")
} else {
    [void]$sb.AppendLine("搜索策略: v0.2.2 方案 H (宽召回 + abstract 二次过滤)")
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
    $if = 'N/A'
    if ($issn -and $journalIf.ContainsKey($issn)) { $if = $journalIf[$issn] }
    $cite = $p.cited_by_count
    $abstract = Restore-Abstract $p.abstract_inverted_index
    if (-not $abstract) { $abstract = 'N/A (OpenAlex 未提供)' }
    $anchor = "title-$num"

    [void]$sb.AppendLine("### # $num <a id=`"$anchor`"></a> $title")
    [void]$sb.AppendLine("")
    [void]$sb.AppendLine("- 作者: $authorsFull")
    [void]$sb.AppendLine("- 年份: $year")
    [void]$sb.AppendLine("- 期刊: $venue")
    [void]$sb.AppendLine("- IF: $if")
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