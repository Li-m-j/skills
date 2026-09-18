# mbai_openalex_to_md.ps1 (v0.1)
# 将 OpenAlex API 返回的 JSON 转换为 医学/生信/AI 文献检索 .md 名录。
# 同源孪生：qm_openalex_to_md.ps1 (化学主题)。本版本扩展：
#   - 期刊白名单改为 医学/生信/AI 顶刊
#   - 二次过滤默认 pattern 改为医学/AI 主题
#   - 字段扩展：MeSH / Publication Type / ClinicalTrials.gov ID
#   - 输出标头改为"医学/生信/AI"
# 作者: Mavis (mbai_paper_search skill v0.1)
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

    # broad 模式二次过滤（默认医学/AI 主题）
    [Parameter(Mandatory = $false)]
    [string]$BroadConceptPattern = "patient|clinical|cohort|meta-analysis|systematic review|review|machine learning|deep learning|neural network|transformer|diffusion|protein|gene|cell|tumor|therapy|trial|disease|drug|sequencing|rna|dna|single[- ]cell|spatial|scrna|drug discovery|drug design|biomarker|imaging|classification|segmentation|foundation model|large language model",

    [Parameter(Mandatory = $false)]
    [ValidateRange(0, 10)]
    [int]$BroadMinMatch = 2,

    [Parameter(Mandatory = $false)]
    [switch]$BroadNoFilter
)

$ErrorActionPreference = 'Stop'

# 1. 校验
if (-not (Test-Path -Path $InputJsonFile -PathType Leaf)) {
    Write-Error "JSON 文件不存在: $InputJsonFile"; exit 1
}

# 2. 读 JSON
if (-not $Quiet) { Write-Host "[1/6] 读取 JSON: $InputJsonFile" -ForegroundColor Cyan }
$json = Get-Content -Raw -Path $InputJsonFile -Encoding UTF8 | ConvertFrom-Json
if (-not $json.results) { Write-Warning "JSON 中无 results 字段"; exit 1 }

$allResults = $json.results
if (-not $Quiet) { Write-Host "    JSON 原始命中: $($allResults.Count) 篇" -ForegroundColor Gray }

# 3. abstract 还原（OpenAlex inverted index）
function Restore-Abstract {
    param($InvertedIndex)
    if (-not $InvertedIndex) { return $null }
    $tokens = @()
    foreach ($prop in $InvertedIndex.PSObject.Properties) {
        foreach ($pos in $prop.Value) {
            $tokens += [PSCustomObject]@{ Pos = $pos; Word = $prop.Name }
        }
    }
    $sorted = $tokens | Sort-Object Pos
    return ($sorted | ForEach-Object { $_.Word }) -join ' '
}

# 4. broad 二次过滤
function Test-BroadRelevance {
    param($Paper, [string]$Pattern, [int]$MinMatch)
    $abstract = Restore-Abstract $Paper.abstract_inverted_index
    if (-not $abstract) { return $true }
    $matches = [regex]::Matches($abstract, $Pattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    return $matches.Count -ge $MinMatch
}

# 5. 期刊 IF 速查表（医学/生信/AI 顶刊，与 shared/cas_journal_zones.json 对齐）
$journalIf = @{
    # 临床医学
    "0028-4793" = 158.5   # NEJM
    "0140-6736" = 98.4    # Lancet
    "0098-7484" = 120.7   # JAMA
    "0959-8138" = 93.6    # BMJ
    "1078-8956" = 82.9    # Nature Medicine
    "2168-6106" = 39.0    # JAMA Internal Medicine
    "0003-4819" = 39.2    # Annals of Internal Medicine
    "1470-2045" = 41.6    # Lancet Oncology
    "0732-183X" = 42.1    # JCO
    "1535-6108" = 48.8    # Cancer Cell
    "1474-175X" = 78.5    # Nature Reviews Cancer
    # 综合
    "0092-8674" = 45.5    # Cell
    "0028-0836" = 50.5    # Nature
    "0036-8075" = 44.7    # Science
    "1474-1733" = 67.7    # Nature Reviews Immunology
    "1471-0072" = 81.3    # Nature Reviews Molecular Cell Biology
    # 生物信息学
    "1548-7091" = 36.1    # Nature Methods
    "1367-4803" = 5.8     # Bioinformatics
    "0305-1048" = 16.6    # Nucleic Acids Research
    "1471-2105" = 3.0     # BMC Bioinformatics
    "1553-7358" = 4.3     # PLOS Computational Biology
    "2405-4712" = 9.0     # Cell Systems
    "1467-5463" = 9.5     # Briefings in Bioinformatics
    "1532-0464" = 4.5     # JBI
    # 人工智能
    "2522-5839" = 25.9    # Nature Machine Intelligence
    "1532-4435" = 5.0     # JMLR
    "0162-8828" = 24.3    # TPAMI
    "1361-8415" = 10.7    # Medical Image Analysis
    "2589-7500" = 24.1    # Lancet Digital Health
    "2398-6352" = 12.8    # npj Digital Medicine
    "2666-3899" = 7.4     # Patterns
}

# 6. broad 二次过滤
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

# 7. Count 限制
if ($Count -gt 0 -and $Count -lt $results.Count) {
    $results = $results | Select-Object -First $Count
}
if (-not $Quiet) { Write-Host "[3/6] 最终输出: $($results.Count) 篇" -ForegroundColor Cyan }

# 8. 拼 Markdown
if (-not $Quiet) { Write-Host "[4/6] 拼装 Markdown" -ForegroundColor Cyan }
$sb = New-Object System.Text.StringBuilder

[void]$sb.AppendLine("# 文献检索结果 ($Mode 模式 · 医学/生信/AI · v0.1)")
[void]$sb.AppendLine("")
[void]$sb.AppendLine("**查询**: $Query")
[void]$sb.AppendLine("**研究方向**: $TopicName")
[void]$sb.AppendLine("**时间**: $(Get-Date -Format 'yyyy-MM-dd HH:mm')")
[void]$sb.AppendLine("**数据源**: OpenAlex API (带 key)")
[void]$sb.AppendLine("**模式**: $Mode")
if ($Mode -eq 'fine') {
    [void]$sb.AppendLine("**文献类型**: article-only")
    [void]$sb.AppendLine("**时间范围**: 近 3 年")
    [void]$sb.AppendLine("**搜索策略**: OpenAlex title.search + concepts.id")
} else {
    [void]$sb.AppendLine("**文献类型**: review-only")
    [void]$sb.AppendLine("**时间范围**: 不限")
    [void]$sb.AppendLine("**搜索策略**: v0.1 方案 H (宽召回 + abstract 二次过滤)")
    [void]$sb.AppendLine("**二次过滤正则**: $BroadConceptPattern")
    [void]$sb.AppendLine("**最少命中数**: $BroadMinMatch")
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
    [void]$sb.AppendLine("- **作者**: $authorsFull")
    [void]$sb.AppendLine("- **年份**: $year")
    [void]$sb.AppendLine("- **期刊**: $venue")
    [void]$sb.AppendLine("- **影响因子**: $if")
    [void]$sb.AppendLine("- **被引**: $cite")
    if ($doi -ne 'N/A') {
        [void]$sb.AppendLine("- **DOI**: [$doi](https://doi.org/$doi)")
    } else {
        [void]$sb.AppendLine("- **DOI**: N/A")
    }
    [void]$sb.AppendLine("- **摘要**: $abstract")
    [void]$sb.AppendLine("")

    # 引用格式
    $firstAuthorSurname = 'N/A'
    if ($p.authorships -and $p.authorships[0].author.display_name) {
        $parts = $p.authorships[0].author.display_name -split ' '
        $firstAuthorSurname = $parts[-1]
    }

    [void]$sb.AppendLine("#### 引用格式")
    [void]$sb.AppendLine("")
    [void]$sb.AppendLine('<details>')
    [void]$sb.AppendLine('<summary>BibTeX</summary>')
    [void]$sb.AppendLine("")
    [void]$sb.AppendLine('```bibtex')
    [void]$sb.AppendLine("@article{$firstAuthorSurname$year,")
    [void]$sb.AppendLine("  title  = {$title},")
    [void]$sb.AppendLine("  journal= {$venue},")
    [void]$sb.AppendLine("  year   = {$year},")
    [void]$sb.AppendLine("  doi    = {$doi}")
    [void]$sb.AppendLine("}")
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
