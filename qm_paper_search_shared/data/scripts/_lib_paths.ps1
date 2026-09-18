# _lib_paths.ps1 (qm_paper_search_shared/data/scripts/)
# 统一解析 data 根目录的 fallback chain。
#
# 用法 A — dot-source:
#   . "$PSScriptRoot\_lib_paths.ps1"
#   $DataDir = Resolve-SharedDataDir
#
# 用法 B — 函数库 (PowerShell 5.1+):
#   Import-LocalizedData 不适用；直接 . 即可
#
# 优先级 (v0.3.0+):
#   1. $env:QM_PAPER_SHARED_DIR (用户/部署侧覆盖)
#   2. 相对 $PSScriptRoot 上溯 1 级（脚本通常在 data/scripts/ 里）
#   3. $env:USERPROFILE\.minimax\skills\qm_paper_search_shared\data (历史默认)
#   4. 抛出错误

function Resolve-SharedDataDir {
    <#
    .SYNOPSIS
        解析 qm_paper_search 共享 data 目录的绝对路径。
    .DESCRIPTION
        按优先级尝试四个来源，返回第一个存在的；都失败则抛错。
    .OUTPUTS
        [string] 绝对路径
    .EXAMPLE
        $DataDir = Resolve-SharedDataDir
    #>
    [CmdletBinding()]
    param()

    # 1. 环境变量
    if ($env:QM_PAPER_SHARED_DIR) {
        if (Test-Path -Path $env:QM_PAPER_SHARED_DIR -PathType Container) {
            return (Resolve-Path -Path $env:QM_PAPER_SHARED_DIR).Path
        }
    }

    # 2. 相对当前脚本位置
    if ($PSScriptRoot) {
        $candidate = Join-Path -Path $PSScriptRoot -ChildPath ".." -Resolve -ErrorAction SilentlyContinue
        if ($candidate) {
            if (Test-Path -Path (Join-Path -Path $candidate -ChildPath "scripts") -PathType Container) {
                return (Resolve-Path -Path $candidate).Path
            }
        }
    }

    # 3. 历史默认
    $default = Join-Path -Path $env:USERPROFILE -ChildPath ".minimax\skills\qm_paper_search_shared\data"
    if (Test-Path -Path $default -PathType Container) {
        return (Resolve-Path -Path $default).Path
    }

    # 4. 全部失败
    $msg = "Cannot resolve qm_paper_search_shared/data directory." + [Environment]::NewLine +
           "Please either:" + [Environment]::NewLine +
           "  (a) set environment variable QM_PAPER_SHARED_DIR to the correct path," + [Environment]::NewLine +
           "  (b) install the skill under $env:USERPROFILE\.minimax\skills\,"
    throw $msg
}
