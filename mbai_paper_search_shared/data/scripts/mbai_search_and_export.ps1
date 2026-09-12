# mbai_search_and_export.ps1 (v0.2)
# 作用：mbai_paper_search_fine / broad 的统一入口脚本
# 设计：探活 → 选源 → 拉数据 → 本地过滤 → seen_papers 落盘 → Markdown 转换
# 用法:
#   .\mbai_search_and_export.ps1 -Query "polygenic risk score" -Mode fine -TopicSlug prs_cancer
#   .\mbai_search_and_export.ps1 -Query "single-cell RNA-seq" -Mode broad -TopicSlug scrna_review -Count 30
#   .\mbai_search_and_export.ps1 -Query "AlphaFold" -Mode fine -TopicSlug alphafold -Count 5 -DryRun
#   .\mbai_search_and_export.ps1 -Query "PD-1 NSCLC" -Mode fine -TopicSlug pd1_nsclc -NewDirection
# 作者: Mavis (mbai_paper_search skill v0.2)
# 日期: 2026-09-09

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Query,

    [Parameter(Mandatory = $true)]
    [ValidateSet('fine', 'broad')]
    [string]$Mode,

    [Parameter(Mandatory = $true)]
    [string]$TopicSlug,

    [Parameter(Mandatory = $false)]
    [ValidateRange(1, 100)]
    [int]$Count = 10,

    [Parameter(Mandatory = $false)]
    [int]$Years = 3,

    [Parameter(Mandatory = $false)]
    [ValidateSet('auto', 'openalex', 'pubmed')]
    [string]$ForceSource = 'auto',

    [Parameter(Mandatory = $false)]
    [switch]$NewDirection,

    [Parameter(Mandatory = $false)]
    [switch]$IncludePreprint,

    [Parameter(Mandatory = $false)]
    [string]$MeshRequired,

    [Parameter(Mandatory = $false)]
    [string]$OutputDir,

    [Parameter(Mandatory = $false)]
    [switch]$DryRun,

    [Parameter(Mandatory = $false)]
    [switch]$AppendUpdateNote
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Amp = [char]38  # '&' 字符（避免 PowerShell 5.1 解析器把 & 当 call operator）
$DataDir = Split-Path -Parent $ScriptDir
$SharedDir = Split-Path -Parent $DataDir
$LocalKeyFile = Join-Path $DataDir 'api_keys.local.json'
$UpdateNotesFile = Join-Path $DataDir 'UPDATE_NOTES.md'
$SeenPapersFile = Join-Path $DataDir 'seen_papers.json'
$UserPrefsFile = Join-Path $DataDir 'user_prefs.json'
$ApiLogsFile = Join-Path $DataDir 'api_logs.json'

# ── 0. 路径 / 时间戳 ─────────────────────────────────────
if (-not $OutputDir) {
    if (Test-Path -Path $UserPrefsFile -PathType Leaf) {
        $prefs = Get-Content -Raw -Path $UserPrefsFile -Encoding UTF8 | ConvertFrom-Json
        $OutputDir = $prefs.default_save_dir
    } else {
        $OutputDir = Join-Path (Split-Path -Parent $SharedDir) 'papers'
    }
}
if (-not (Test-Path -Path $OutputDir -PathType Container)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}
$today = Get-Date -Format 'yyyyMMdd'
$outFile = Join-Path $OutputDir "paper_search_${Mode}_${TopicSlug}_${today}.md"

# ── 0.5 PII 脱敏检查 (#11) ───────────────────────────────
$piiPattern = '\b\d{13,18}\b'
if ($Query -match $piiPattern) {
    Write-Warning "⚠ 查询字符串检测到 13-18 位连续数字（疑似患者 ID / 信用卡号 / 身份证号）。"
    Write-Warning "  强烈建议脱敏后再检索（隐私风险）。"
    if (-not $DryRun) {
        $confirm = Read-Host "  是否继续？(y/N)"
        if ($confirm -ne 'y' -and $confirm -ne 'Y') {
            Write-Host "  退出，未检索。" -ForegroundColor Yellow
            exit 0
        }
    }
}

# ── 1. API 健康度日志 (#7) ──────────────────────────────
function Write-ApiLog {
    param(
        [string]$Endpoint,
        [string]$Source,
        [int]$Status,
        [int]$LatencyMs,
        [string]$Note = ''
    )
    $entry = [ordered]@{
        ts       = (Get-Date).ToString('o')
        source   = $Source
        endpoint = $Endpoint
        status   = $Status
        latency  = $LatencyMs
        note     = $Note
    } | ConvertTo-Json -Compress
    if (-not (Test-Path -Path $ApiLogsFile -PathType Leaf)) {
        '[]' | Out-File -FilePath $ApiLogsFile -Encoding UTF8
    }
    $logs = Get-Content -Raw -Path $ApiLogsFile -Encoding UTF8 | ConvertFrom-Json
    if (-not $logs) { $logs = @() }
    $logs = @($logs) + ($entry | ConvertFrom-Json)
    $logs = $logs | Select-Object -Last 500
    $logs | ConvertTo-Json -Depth 3 | Out-File -FilePath $ApiLogsFile -Encoding UTF8
}

# ── 2. 加载 key（local 文件 > 环境变量）────────────────
function Get-Key {
    param([string]$Provider)
    $envName = switch ($Provider) {
        'openalex'         { 'OPENALEX_API_KEY' }
        'semantic_scholar' { 'SEMANTIC_SCHOLAR_API_KEY' }
        'ncbi'             { 'NCBI_API_KEY' }
        default { '' }
    }
    if ($LocalKeyFile -and (Test-Path -Path $LocalKeyFile -PathType Leaf)) {
        $cfg = Get-Content -Raw -Path $LocalKeyFile -Encoding UTF8 | ConvertFrom-Json
        if ($cfg.providers.$Provider.key) { return $cfg.providers.$Provider.key }
    }
    if ($envName) {
        $envVal = [Environment]::GetEnvironmentVariable($envName, 'User')
        if ($envVal) { return $envVal }
    }
    return $null
}

# ── 3. OpenAlex 探活 (#1) ──────────────────────────────
function Test-OpenAlexHealth {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $key = Get-Key 'openalex'
    $url = 'https://api.openalex.org/works?per_page=1'
    if ($key) { $url = $url + $Amp + "api_key=$key" }
    try {
        $resp = Invoke-RestMethod -Uri $url -Method GET -TimeoutSec 15
        $sw.Stop()
        $metaCount = if ($resp.meta.count) { [int]$resp.meta.count } else { 0 }
        Write-ApiLog -Endpoint $url -Source 'openalex' -Status 200 -LatencyMs $sw.ElapsedMilliseconds -Note "probe meta_count=$metaCount"
        return ($metaCount -gt 0)
    } catch {
        $sw.Stop()
        $code = $_.Exception.Response.StatusCode.value__
        Write-ApiLog -Endpoint $url -Source 'openalex' -Status $code -LatencyMs $sw.ElapsedMilliseconds -Note "probe FAIL: $($_.Exception.Message)"
        return $false
    }
}

# ── 4. PubMed 探活 ──────────────────────────────────────
function Test-PubMedHealth {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $key = Get-Key 'ncbi'
    $url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi?db=pubmed'
    if ($key) { $url = $url + $Amp + "api_key=$key" }
    $url += '&tool=mbai_paper_search&email=mavis.test@example.com'
    try {
        $resp = Invoke-WebRequest -Uri $url -Method GET -TimeoutSec 15 -UseBasicParsing
        $sw.Stop()
        $code = [int]$resp.StatusCode
        Write-ApiLog -Endpoint $url -Source 'pubmed' -Status $code -LatencyMs $sw.ElapsedMilliseconds -Note 'probe'
        return ($code -eq 200)
    } catch {
        $sw.Stop()
        $code = $_.Exception.Response.StatusCode.value__
        Write-ApiLog -Endpoint $url -Source 'pubmed' -Status $code -LatencyMs $sw.ElapsedMilliseconds -Note "probe FAIL: $($_.Exception.Message)"
        return $false
    }
}

# ── 5. 选源（#1 主源探活 → 切兜底）────────────────────
Write-Host "[1/8] 主源健康度探活..." -ForegroundColor Cyan
$useOpenAlex = $false
$usePubMed = $false
$sourceNote = ''

if ($ForceSource -eq 'openalex') {
    $useOpenAlex = $true
    $sourceNote = '强制 OpenAlex（未做探活）'
} elseif ($ForceSource -eq 'pubmed') {
    $usePubMed = $true
    $sourceNote = '强制 PubMed（未做探活）'
} else {
    $oa = Test-OpenAlexHealth
    $pm = Test-PubMedHealth
    if ($oa) {
        $useOpenAlex = $true
        $sourceNote = 'OpenAlex 健康（默认）'
    } elseif ($pm) {
        $usePubMed = $true
        $sourceNote = 'OpenAlex 异常 → 切 PubMed (#1 兜底)'
        Write-Warning "⚠ OpenAlex API 异常，自动切到 PubMed（mbai §3 兜底链 #1）"
    } else {
        Write-Error "✗ OpenAlex 与 PubMed 均不可用，请检查网络或稍后重试"
        exit 1
    }
}
Write-Host "    $sourceNote" -ForegroundColor Gray

# ── 6. 数据采集 ────────────────────────────────────────
$records = @()
$dataSourceTag = ''

if ($useOpenAlex) {
    Write-Host "[2/8] OpenAlex 检索三段式 (#2 改进)..." -ForegroundColor Cyan
    $key = Get-Key 'openalex'

    # 段 1：小池试探（per_page=1，看命中数）
    $probeUrl = "https://api.openalex.org/works?search=$([uri]::EscapeDataString($Query))&per_page=1"
    if ($key) { $probeUrl = $probeUrl + $Amp + "api_key=$key" }
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $probe = Invoke-RestMethod -Uri $probeUrl -Method GET -TimeoutSec 30
    $sw.Stop()
    $probeCount = if ($probe.meta.count) { [int]$probe.meta.count } else { 0 }
    Write-Host "    段1 试探：meta_count=$probeCount（耗时 $($sw.ElapsedMilliseconds)ms）" -ForegroundColor Gray
    Write-ApiLog -Endpoint $probeUrl -Source 'openalex' -Status 200 -LatencyMs $sw.ElapsedMilliseconds -Note "probe-search meta=$probeCount"

    if ($probeCount -eq 0) {
        Write-Warning "  试探为 0，尝试放宽 query（去掉连字符 / 拆词）"
        $relaxed = $Query -replace '[-_]', ' '
        $probeUrl2 = "https://api.openalex.org/works?search=$([uri]::EscapeDataString($relaxed))&per_page=1"
        if ($key) { $probeUrl2 = $probeUrl2 + $Amp + "api_key=$key" }
        $probe = Invoke-RestMethod -Uri $probeUrl2 -Method GET -TimeoutSec 30
        $probeCount = if ($probe.meta.count) { [int]$probe.meta.count } else { 0 }
        Write-Host "    段1 重试（放宽）：meta_count=$probeCount" -ForegroundColor Gray
    }

    if ($probeCount -eq 0) {
        Write-Warning "  OpenAlex 仍为 0，强制切 PubMed"
        $useOpenAlex = $false
        $usePubMed = $true
    } else {
        # 段 2：拉主池（per_page=3 分页，避免 per_page>=10 触发 0 bug；#3 日期本地过滤）
        $perPage = 3
        $pages = [Math]::Ceiling($Count * 2 / $perPage)  # 多拉一倍给本地过滤留余量
        $pool = @()
        for ($p = 1; $p -le $pages; $p++) {
            $u = "https://api.openalex.org/works?search=$([uri]::EscapeDataString($Query))&per_page=$perPage&page=$p"
            if ($key) { $u = $u + $Amp + "api_key=$key" }
            try {
                $r = Invoke-RestMethod -Uri $u -Method GET -TimeoutSec 30
                if ($r.results.Count -eq 0) { break }
                $pool += $r.results
            } catch {
                Write-Warning "  page=$p 失败: $($_.Exception.Message)"
                break
            }
            Start-Sleep -Milliseconds 200
        }
        Write-Host "    段2 主池：拉回 $($pool.Count) 篇（要求 $Count 篇 ×2 余量）" -ForegroundColor Gray

        # 段 3：本地过滤（年份 + 类型 + 关键词）
        $currentYear = (Get-Date).Year
        $minYear = $currentYear - $Years
        $filterType = if ($Mode -eq 'broad') { 'review' } else { 'article' }
        $kwPattern = if ($Query) { [string]::Join('|', @($Query -split '\s+' | Select-Object -First 3)) } else { '' }

        $records = foreach ($r in $pool) {
            if ($r.publication_year -lt $minYear) { continue }
            if ($filterType -eq 'article' -and $r.type -notin @('article', 'letter')) { continue }
            if ($filterType -eq 'review' -and $r.type -ne 'review') { continue }
            $r
        }
        Write-Host "    段3 本地过滤（年份 $minYear-$currentYear · 类型 $filterType）：剩 $($records.Count) 篇" -ForegroundColor Gray

        # 如果不够，拉更多页
        $attempts = 0
        while ($records.Count -lt $Count -and $attempts -lt 3) {
            $attempts++
            $extraPage = $pages + $attempts
            $u = "https://api.openalex.org/works?search=$([uri]::EscapeDataString($Query))&per_page=$perPage&page=$extraPage"
            if ($key) { $u = $u + $Amp + "api_key=$key" }
            try {
                $r = Invoke-RestMethod -Uri $u -Method GET -TimeoutSec 30
                if ($r.results.Count -eq 0) { break }
                foreach ($x in $r.results) {
                    if ($x.publication_year -lt $minYear) { continue }
                    if ($filterType -eq 'article' -and $x.type -notin @('article', 'letter')) { continue }
                    if ($filterType -eq 'review' -and $x.type -ne 'review') { continue }
                    $records += $x
                    if ($records.Count -ge $Count * 2) { break }
                }
            } catch { break }
            Start-Sleep -Milliseconds 200
        }

        $records = $records | Select-Object -First $Count
        $dataSourceTag = "OpenAlex API $(if ($key) { '(with key)' } else { '(no key)' })"
    }
}

if ($usePubMed) {
    Write-Host "[2/8] PubMed 检索（#1 兜底链）..." -ForegroundColor Cyan
    $key = Get-Key 'ncbi'

    $term = $Query
    if ($Mode -eq 'broad') { $term += ' AND (Review[Publication Type] OR Systematic Review[Publication Type] OR Meta-Analysis[Publication Type])' }
    $reldate = $Years * 365
    $retmax = [Math]::Max($Count * 3, 30)
    $sort = if ($Mode -eq 'broad') { 'relevance' } else { 'relevance' }

    $sUrl = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=$([uri]::EscapeDataString($term))&retmode=json&retmax=$retmax&reldate=$reldate&datetype=pdat&sort=$sort&tool=mbai_paper_search&email=mavis.test@example.com"
    if ($key) { $sUrl = $sUrl + $Amp + "api_key=$key" }

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $sResp = Invoke-RestMethod -Uri $sUrl -Method GET -TimeoutSec 30
    $sw.Stop()
    $totalHits = [int]$sResp.esearchresult.count
    $idList = @($sResp.esearchresult.idlist)
    Write-Host "    esearch 命中 $totalHits 篇，返回 $($idList.Count) 个 PMID（耗时 $($sw.ElapsedMilliseconds)ms）" -ForegroundColor Gray
    Write-ApiLog -Endpoint $sUrl -Source 'pubmed' -Status 200 -LatencyMs $sw.ElapsedMilliseconds -Note "esearch hits=$totalHits"

    if ($idList.Count -gt 0) {
        # 段 2：拉详情（esummary + efetch 完整作者 + abstract + MeSH）
        $idStr = [string]::Join(',', $idList)
        $sumUrl = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=$idStr&retmode=json&tool=mbai_paper_search&email=mavis.test@example.com"
        if ($key) { $sumUrl = $sumUrl + $Amp + "api_key=$key" }
        $fetchUrl = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=$idStr&rettype=xml&retmode=xml&tool=mbai_paper_search&email=mavis.test@example.com"
        if ($key) { $fetchUrl = $fetchUrl + $Amp + "api_key=$key" }

        $sw2 = [System.Diagnostics.Stopwatch]::StartNew()
        $summ = Invoke-RestMethod -Uri $sumUrl -Method GET -TimeoutSec 30
        $xmlText = (Invoke-WebRequest -Uri $fetchUrl -Method GET -TimeoutSec 60 -UseBasicParsing).Content
        $sw2.Stop()
        Write-Host "    esummary+efetch 拉取详情（$($idList.Count) 篇，耗时 $($sw2.ElapsedMilliseconds)ms）" -ForegroundColor Gray
        Write-ApiLog -Endpoint $fetchUrl -Source 'pubmed' -Status 200 -LatencyMs $sw2.ElapsedMilliseconds -Note "efetch ids=$($idList.Count)"

        $xml = [xml]$xmlText
        $recs = $xml.SelectNodes('//PubmedArticle')

        # 段 3：组装 records（结构统一，便于后续 SS tldr 补全与转换）
        $records = foreach ($rec in $recs) {
            $pmid = $rec.SelectSingleNode('MedlineCitation/PMID').InnerText
            $s = $summ.result.$pmid
            $title = $s.title
            $pubDate = $s.pubdate
            $year = if ($pubDate -match '^\d{4}') { $pubDate.Substring(0,4) } else { 'N/A' }
            $journal = $s.fulljournalname
            $doiNode = $rec.SelectSingleNode("MedlineCitation/Article/ELocationID[@EIdType='doi']")
            $doi = if ($doiNode) { $doiNode.InnerText } else { 'N/A' }

            # 完整作者列表（#5 改进：从 efetch XML 的 AuthorList 解析，不再依赖 esummary 截断版）
            $authorNodes = $rec.SelectNodes('MedlineCitation/Article/AuthorList/Author')
            $authorsFull = if ($authorNodes.Count -gt 0) {
                $names = @()
                foreach ($a in $authorNodes) {
                    $last = $a.LastName
                    $initials = $a.ForeName
                    $collective = $a.CollectiveName
                    if ($collective) { $names += $collective }
                    elseif ($last -and $initials) { $names += "$last $initials" }
                    else { $names += $a.InnerText }
                }
                [string]::Join(', ', $names)
            } else { 'N/A' }

            $firstAuthor = if ($authorNodes.Count -gt 0) {
                $first = $authorNodes[0]
                if ($first.CollectiveName) { $first.CollectiveName }
                elseif ($first.LastName) { "$($first.LastName) $($first.ForeName)" }
                else { 'N/A' }
            } else { 'N/A' }

            $meshAllArr = @()
            foreach ($m in $rec.SelectNodes('MedlineCitation/MeshHeadingList/MeshHeading/DescriptorName')) { $meshAllArr += $m.InnerText }
            $meshAll = [string]::Join('; ', $meshAllArr)
            $meshMajorArr = @()
            foreach ($m in $rec.SelectNodes('MedlineCitation/MeshHeadingList/MeshHeading/DescriptorName[@MajorTopic="Y"]')) { $meshMajorArr += $m.InnerText }
            $meshMajor = [string]::Join('; ', $meshMajorArr)
            $ptArr = @()
            foreach ($p in $rec.SelectNodes('MedlineCitation/Article/PublicationTypeList/PublicationType')) { $ptArr += $p.InnerText }
            $pt = [string]::Join(', ', $ptArr)

            $absText = ''
            $absNode = $rec.SelectSingleNode('MedlineCitation/Article/Abstract')
            if ($absNode) {
                foreach ($ab in $absNode.SelectNodes('AbstractText')) {
                    $label = $ab.GetAttribute('Label')
                    $text = $ab.InnerText
                    $absText += "$(if ($label) { "[$label] " })$text`n`n"
                }
            }
            if (-not $absText) { $absText = 'N/A' }

            [PSCustomObject]@{
                pmid         = $pmid
                doi          = $doi
                title        = $title
                year         = $year
                pubDate      = $pubDate
                journal      = $journal
                authorsFull  = $authorsFull
                firstAuthor  = $firstAuthor
                meshAll      = $meshAll
                meshMajor    = $meshMajor
                pubType      = $pt
                abstract     = $absText
                source       = 'pubmed'
                tldr         = 'N/A'
                citedByCount = 'N/A'
            }
        }
        $records = @($records) | Select-Object -First $Count
        $dataSourceTag = "PubMed E-utilities $(if ($key) { '(with NCBI key)' } else { '(no key, 3 req/s)' })"
    }
}

if ($records.Count -eq 0) {
    Write-Error "✗ 无可用结果。请检查 query 或扩大检索范围。"
    exit 1
}
Write-Host "    最终: $($records.Count) 篇" -ForegroundColor Green

# ── 7. SS tldr 补全 (#4) ──────────────────────────────
Write-Host "[3/8] 补全 Semantic Scholar tldr (#4 改进)..." -ForegroundColor Cyan
$ssKey = Get-Key 'semantic_scholar'
$ssHeaders = @{}
if ($ssKey) { $ssHeaders['x-api-key'] = $ssKey }
$ssFilled = 0
foreach ($rec in $records) {
    if ($rec.doi -eq 'N/A') { continue }
    $ssUrl = "https://api.semanticscholar.org/graph/v1/paper/DOI:$($rec.doi)?fields=tldr,citationCount"
    try {
        $ssR = Invoke-RestMethod -Uri $ssUrl -Method GET -Headers $ssHeaders -TimeoutSec 15
        if ($ssR.tldr -and $ssR.tldr.text) {
            $rec.tldr = $ssR.tldr.text
            $ssFilled++
        }
        if ($ssR.citationCount -ne $null) { $rec.citedByCount = [int]$ssR.citationCount }
        Write-ApiLog -Endpoint $ssUrl -Source 'semantic_scholar' -Status 200 -LatencyMs 0 -Note "tldr ok"
    } catch {
        $code = $_.Exception.Response.StatusCode.value__
        if ($code -eq 429) {
            Write-Warning "  SS 429 限流，跳过剩余条目的 tldr"
            Write-ApiLog -Endpoint $ssUrl -Source 'semantic_scholar' -Status 429 -LatencyMs 0 -Note "rate limited"
            break
        }
        Write-ApiLog -Endpoint $ssUrl -Source 'semantic_scholar' -Status $(if ($code) { $code } else { 0 }) -LatencyMs 0 -Note "tldr fail: $($_.Exception.Message)"
    }
    Start-Sleep -Milliseconds 100
}
Write-Host "    SS tldr 补全：$ssFilled/$($records.Count) 篇成功" -ForegroundColor Gray

# ── 8. seen_papers 落盘 (#8) ───────────────────────────
Write-Host "[4/8] seen_papers.json 落盘 (#8 改进)..." -ForegroundColor Cyan
if (-not (Test-Path -Path $SeenPapersFile -PathType Leaf)) {
    '{"version":"0.1.0","topics":{}}' | Out-File -FilePath $SeenPapersFile -Encoding UTF8
}
$sp = Get-Content -Raw -Path $SeenPapersFile -Encoding UTF8 | ConvertFrom-Json
if (-not $sp.topics) { $sp.topics = @{} }

$topicId = if ($Mode -eq 'fine') { "fine_$TopicSlug" } else { "broad_$TopicSlug" }
$existing = $sp.topics.$topicId
$seenPmid = @()
$seenDoi = @()
if ($existing) {
    $seenPmid = @($existing.seen_pmids)
    $seenDoi = @($existing.seen_dois)
}
foreach ($rec in $records) {
    if ($rec.pmid -and ($seenPmid -notcontains $rec.pmid)) { $seenPmid += $rec.pmid }
    if ($rec.doi -and $rec.doi -ne 'N/A' -and ($seenDoi -notcontains $rec.doi)) { $seenDoi += $rec.doi }
}

$topicData = [ordered]@{
    name        = $TopicSlug
    query       = $Query
    mode        = $Mode
    created_at  = if ($existing.created_at) { $existing.created_at } else { (Get-Date -Format 'yyyy-MM-dd') }
    last_used   = (Get-Date -Format 'yyyy-MM-dd')
    last_query  = $Query
    seen_pmids  = @($seenPmid)
    seen_dois   = @($seenDoi)
    data_source = $dataSourceTag
    version     = '0.2'
}
$sp.topics | Add-Member -NotePropertyName $topicId -NotePropertyValue $topicData -Force
$sp | ConvertTo-Json -Depth 10 | Out-File -FilePath $SeenPapersFile -Encoding UTF8
Write-Host "    topic_id=$topicId 累计去重池：$(@($seenPmid).Count) PMID / $(@($seenDoi).Count) DOI" -ForegroundColor Gray

# ── 9. Markdown 拼装（按 SKILL.md §6.1）────────────────
Write-Host "[5/8] Markdown 拼装..." -ForegroundColor Cyan
$sb = New-Object System.Text.StringBuilder

[void]$sb.AppendLine("# 文献检索结果（精细模式 · 医学/生信/AI · v0.2）")
[void]$sb.AppendLine("")
[void]$sb.AppendLine("**查询**：$Query")
[void]$sb.AppendLine("**研究方向**：$TopicSlug")
[void]$sb.AppendLine("**时间范围**：$((Get-Date).Year - $Years)–$((Get-Date).Year)")
[void]$sb.AppendLine("**文献类型**：$(if ($Mode -eq 'broad') { 'review-only' } else { 'article-only' })")
[void]$sb.AppendLine("**数据源**：$dataSourceTag")
[void]$sb.AppendLine("**检索时间**：$(Get-Date -Format 'yyyy-MM-dd HH:mm')")
[void]$sb.AppendLine("**检索脚本**：mbai_search_and_export.ps1 v0.2（探活 + 选源 + 三段式）")
[void]$sb.AppendLine("")

# 速览表
[void]$sb.AppendLine("## 📋 速览（$($records.Count) 篇）")
[void]$sb.AppendLine("")
[void]$sb.AppendLine("| # | 标题 | 作者 | 年份 | DOI | 被引 |")
[void]$sb.AppendLine("|---|------|------|------|-----|------|")
for ($i = 0; $i -lt $records.Count; $i++) {
    $rec = $records[$i]
    $num = $i + 1
    $titleEsc = $rec.title -replace '\|', '\|'
    $authors = $rec.firstAuthor
    if ($rec.authorsFull -and $rec.authorsFull -ne 'N/A') {
        $others = ($rec.authorsFull -split ', ' | Select-Object -Skip 1 | Measure-Object).Count
        if ($others -gt 0) { $authors += " et al. (+$others)" }
    } else { $authors = 'N/A' }
    $year = $rec.year
    $doi = $rec.doi
    $anchor = "title-$num"
    $cite = $rec.citedByCount
    if ($doi -ne 'N/A') {
        [void]$sb.AppendLine("| $num | [$titleEsc](#$anchor) | $authors | $year | [$doi](https://doi.org/$doi) | $cite |")
    } else {
        [void]$sb.AppendLine("| $num | [$titleEsc](#$anchor) | $authors | $year | N/A | $cite |")
    }
}
[void]$sb.AppendLine("")

# 期刊分区白名单（来自 cas_journal_zones.json）
$zonesFile = Join-Path $DataDir 'cas_journal_zones.json'
$zoneMap = @{}
if (Test-Path -Path $zonesFile -PathType Leaf) {
    $zd = Get-Content -Raw -Path $zonesFile -Encoding UTF8 | ConvertFrom-Json
    foreach ($prop in $zd.journals.PSObject.Properties) {
        $j = $prop.Value
        $zoneMap[$prop.Name] = $j
    }
}

# 1区 / Top 统计
$topCount = 0
$zone1Count = 0
foreach ($rec in $records) {
    $info = $zoneMap[$rec.journal]
    if ($info) {
        if ($info.top) { $topCount++ }
        if ($info.zone -eq '1') { $zone1Count++ }
    }
}
[void]$sb.AppendLine("> ⭐ Top $topCount 篇 · 1 区 $zone1Count 篇 · 🔴 预警 0 篇 · 已跳过重复 0 篇 · 含 MeSH $(@($records | Where-Object { $_.meshAll -ne '' }).Count) 篇 · 含临床试验注册号 $(@($records | Where-Object { $_.pubType -match 'Trial' }).Count) 篇")
[void]$sb.AppendLine("")
[void]$sb.AppendLine("---")
[void]$sb.AppendLine("")
[void]$sb.AppendLine("## 📚 详细条目")
[void]$sb.AppendLine("")

for ($i = 0; $i -lt $records.Count; $i++) {
    $rec = $records[$i]
    $num = $i + 1
    $anchor = "title-$num"
    $info = $zoneMap[$rec.journal]
    $zone = if ($info) { $info.zone } else { 'N/A' }
    $top = if ($info -and $info.top) { '⭐ Top' } else { '' }
    $if_ = if ($info) { $info.if_2024 } else { 'N/A' }
    $warning = if ($info -and $info.warning) { '🔴 预警' } else { '' }
    $tagArr = @()
    if ($top) { $tagArr += $top }
    $tagArr += "$zone 区"
    if ($warning) { $tagArr += $warning }
    $tagStr = [string]::Join(' / ', $tagArr)
    if (-not $tagStr) { $tagStr = 'N/A' }

    # 证据等级标签
    $pt = $rec.pubType
    $ptTags = @()
    if ($pt -match 'Randomized') { $ptTags += 'RCT' }
    if ($pt -match 'Meta-Analysis') { $ptTags += 'Meta-analysis' }
    if ($pt -match 'Systematic Review') { $ptTags += 'Systematic Review' }
    if ($pt -match 'Observational Study') { $ptTags += 'Cohort/Observational' }
    if ($pt -match 'Comparative Study') { $ptTags += 'Comparative Study' }
    if ($pt -match 'Pragmatic Clinical Trial') { $ptTags += 'Pragmatic Trial' }
    if ($pt -match 'Multicenter Study') { $ptTags += 'Multicenter' }
    if (-not $ptTags) {
        if ($pt -match 'Review') { $ptTags += 'Review' }
        else { $ptTags += 'Article' }
    }
    $ptStr = [string]::Join(' / ', $ptTags)

    [void]$sb.AppendLine("### # $num <a id=`"$anchor`"></a> $($rec.title)")
    [void]$sb.AppendLine("")
    [void]$sb.AppendLine("- **作者**（仅来自 PubMed API）：$($rec.authorsFull)")
    [void]$sb.AppendLine("- **第一作者**：$($rec.firstAuthor)")
    [void]$sb.AppendLine("- **年份**：$($rec.year)（PubDate: $($rec.pubDate)）")
    [void]$sb.AppendLine("- **期刊**：$($rec.journal)（$tagStr）")
    [void]$sb.AppendLine("- **影响因子**：$if_")
    if ($rec.doi -ne 'N/A') {
        [void]$sb.AppendLine("- **DOI**：[${rec.doi}](https://doi.org/${rec.doi})")
    } else { [void]$sb.AppendLine("- **DOI**：N/A") }
    if ($rec.pmid) {
        [void]$sb.AppendLine("- **PMID**：$($rec.pmid) · [PubMed 链接](https://pubmed.ncbi.nlm.nih.gov/$($rec.pmid)/)")
    }
    [void]$sb.AppendLine("- **被引次数**（Semantic Scholar）：$($rec.citedByCount)")
    [void]$sb.AppendLine("- **证据等级 / Publication Type**：$ptStr")
    if ($rec.meshMajor) { [void]$sb.AppendLine("- **MeSH 主题词（Major Topic）**：$($rec.meshMajor)") }
    [void]$sb.AppendLine("- **MeSH 主题词（全部）**：$(if ($rec.meshAll.Length -gt 400) { $rec.meshAll.Substring(0, 400) + '...' } else { $rec.meshAll })")
    $kw = if ($rec.meshMajor) { $rec.meshMajor } elseif ($rec.meshAll) { [string]::Join(', ', @($rec.meshAll -split '; ' | Select-Object -First 5)) } else { 'N/A' }
    [void]$sb.AppendLine("- **关键词**：$kw")
    [void]$sb.AppendLine("- **摘要原文（来自 PubMed）**：")
    [void]$sb.AppendLine("")
    if ($rec.abstract -ne 'N/A') {
        [void]$sb.AppendLine('  > ' + ($rec.abstract.Trim() -replace "`n", "`n  > "))
    } else { [void]$sb.AppendLine("  > N/A") }
    [void]$sb.AppendLine("")
    if ($rec.tldr -ne 'N/A') {
        [void]$sb.AppendLine("- **TLDR**（Semantic Scholar AI 总结）：$($rec.tldr)")
    } else {
        [void]$sb.AppendLine("- **TLDR**（Semantic Scholar AI 总结）：N/A（无 SS tldr 字段）")
    }
    [void]$sb.AppendLine("")

    # 引用格式（4 种）
    $firstAuthorSurname = 'N/A'
    if ($rec.firstAuthor -and $rec.firstAuthor -ne 'N/A') {
        $parts = $rec.firstAuthor -split ' '
        $firstAuthorSurname = $parts[-1]
    }

    [void]$sb.AppendLine("#### 📎 引用格式")
    [void]$sb.AppendLine("")
    [void]$sb.AppendLine('<details>')
    [void]$sb.AppendLine('<summary>BibTeX</summary>')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('```bibtex')
    [void]$sb.AppendLine("@article{${firstAuthorSurname}$($rec.year),")
    [void]$sb.AppendLine("  title  = {$($rec.title)},")
    [void]$sb.AppendLine("  author = {$($rec.authorsFull)},")
    [void]$sb.AppendLine("  journal= {$($rec.journal)},")
    [void]$sb.AppendLine("  year   = {$($rec.year)},")
    if ($rec.doi -ne 'N/A') { [void]$sb.AppendLine("  doi    = {$($rec.doi)},") }
    if ($rec.pmid) { [void]$sb.AppendLine("  pmid   = {$($rec.pmid)}") }
    [void]$sb.AppendLine('}')
    [void]$sb.AppendLine('```')
    [void]$sb.AppendLine('</details>')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('<details>')
    [void]$sb.AppendLine('<summary>APA 7</summary>')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine("$($rec.firstAuthor) et al. ($($rec.year)). $($rec.title). *$($rec.journal)*. https://doi.org/$($rec.doi)")
    [void]$sb.AppendLine('</details>')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('<details>')
    [void]$sb.AppendLine('<summary>GB/T 7714</summary>')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine("$($rec.firstAuthor) 等. $($rec.title)[$($rec.journal)]. $($rec.year). DOI: $($rec.doi).")
    [void]$sb.AppendLine('</details>')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('<details>')
    [void]$sb.AppendLine('<summary>RIS</summary>')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('```')
    [void]$sb.AppendLine("TY  - JOUR")
    [void]$sb.AppendLine("TI  - $($rec.title)")
    [void]$sb.AppendLine("AU  - $($rec.firstAuthor)")
    [void]$sb.AppendLine("PY  - $($rec.year)")
    [void]$sb.AppendLine("JO  - $($rec.journal)")
    if ($rec.doi -ne 'N/A') { [void]$sb.AppendLine("DO  - $($rec.doi)") }
    if ($rec.pmid) {
        [void]$sb.AppendLine("AN  - $($rec.pmid)")
        [void]$sb.AppendLine("UR  - https://pubmed.ncbi.nlm.nih.gov/$($rec.pmid)/")
    }
    [void]$sb.AppendLine("ER  - ")
    [void]$sb.AppendLine('```')
    [void]$sb.AppendLine('</details>')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('---')
    [void]$sb.AppendLine('')
}

# 评估
[void]$sb.AppendLine("## 检索结果评估")
[void]$sb.AppendLine("")
[void]$sb.AppendLine("| 维度 | 数值 |")
[void]$sb.AppendLine("|---|---|")
[void]$sb.AppendLine("| 数据源 | $dataSourceTag |")
[void]$sb.AppendLine("| 检索脚本 | mbai_search_and_export.ps1 v0.2 |")
[void]$sb.AppendLine("| 主源探活 | $sourceNote |")
[void]$sb.AppendLine("| 返回数 | $($records.Count) 篇 |")
[void]$sb.AppendLine("| 1 区 | $zone1Count 篇 |")
[void]$sb.AppendLine("| ⭐ Top | $topCount 篇 |")
[void]$sb.AppendLine("| SS tldr 补全 | $ssFilled/$($records.Count) 篇 |")
[void]$sb.AppendLine("| 去重池 topic_id | $topicId |")
[void]$sb.AppendLine("")
[void]$sb.AppendLine("> ⚠️ 临床决策需原文 + 当前指南。本工具输出仅作学术调研辅助。")
[void]$sb.AppendLine("")

# 落盘
if ($DryRun) {
    Write-Host "[6/8] DryRun：未写文件" -ForegroundColor Yellow
    Write-Host "    预览（前 800 字符）：" -ForegroundColor Gray
    Write-Host ($sb.ToString().Substring(0, [Math]::Min(800, $sb.ToString().Length)))
} else {
    [void]$sb.AppendLine("<!-- generated by mbai_search_and_export.ps1 v0.2 at $(Get-Date -Format 'o') -->")
    $utf8 = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($outFile, $sb.ToString(), $utf8)
    $f = Get-Item $outFile
    Write-Host "[6/8] 写入：$outFile ($($f.Length) bytes)" -ForegroundColor Green
}

# ── 10. UPDATE_NOTES 增量 (#10) ───────────────────────
if ($AppendUpdateNote -and -not $DryRun) {
    Write-Host "[7/8] UPDATE_NOTES 增量 (#10 改进)..." -ForegroundColor Cyan
    $note = @"
- v0.2 ($(Get-Date -Format 'yyyy-MM-dd')) · query="$Query" mode=$Mode topic=$TopicSlug
  - 数据源: $dataSourceTag
  - 主源探活: $sourceNote
  - 命中: $($records.Count) 篇
  - SS tldr: $ssFilled/$($records.Count)
  - 去重池: $topicId (累计 $((@($seenPmid)).Count) PMID)
"@
    Add-Content -Path $UpdateNotesFile -Value $note -Encoding UTF8
}

# ── 11. 总结 ───────────────────────────────────────
Write-Host "[8/8] Done." -ForegroundColor Green
Write-Host "  topic_id: $topicId"
Write-Host "  data_source: $dataSourceTag"
Write-Host "  records: $($records.Count)"
Write-Host "  output: $outFile"
