# 恢复 Windows Defender 并加排除项
#
# 背景：这台机器装过 Reason Cybersecurity，卸载后残留了安全中心记录，
# 同时把 Defender 关掉了（实时保护/病毒防护都是 False）。
# 现在等于完全没防护。本脚本做：
#   1. 去掉「禁用 Defender」的组策略/注册表项
#   2. 打开实时保护与防病毒
#   3. 把本程序与微信目录加进排除项（避免它误杀我们的自动化脚本）
#   4. 结果写 def-recover.log（不提权也能读）

$ErrorActionPreference = 'Continue'

function Test-Admin {
    $p = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Admin)) {
    Write-Host "[X] 需要管理员权限。请双击同目录的「恢复防护并加白名单.bat」。" -ForegroundColor Red
    Read-Host "按回车退出"
    exit 1
}

$log = New-Object System.Collections.ArrayList
function Say($msg, $color = 'Gray') {
    Write-Host $msg -ForegroundColor $color
    [void]$log.Add($msg)
}

Say "==============================================" 'Cyan'
Say "  恢复 Windows Defender + 加排除项" 'Cyan'
Say "==============================================" 'Cyan'
Say ""

# ---------- 1. 清掉禁用策略 ----------
Say "== 1. 检查禁用策略 =="
$policy = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows Defender'
$removed = @()
foreach ($name in @('DisableAntiSpyware', 'DisableRealtimeMonitoring')) {
    try {
        $v = Get-ItemProperty -Path $policy -Name $name -ErrorAction Stop
        if ($null -ne $v.$name) {
            New-ItemProperty -Path $policy -Name $name -Value 0 -PropertyType DWord -Force | Out-Null
            $removed += $name
            Say "  已清零策略：$name（原来不是 0）" 'Green'
        } else {
            Say "  策略 $name 已是 0"
        }
    } catch {
        Say "  没有策略项：$name"
    }
}
if ($removed.Count -gt 0) { Say "  策略改动需要重启才完全生效" 'Yellow' }

# ---------- 2. 打开防护 ----------
Say ""
Say "== 2. 打开实时保护 =="
$okRT = $false
try {
    Set-MpPreference -DisableRealtimeMonitoring $false -ErrorAction Stop
    $okRT = $true
    Say "  Set-MpPreference -DisableRealtimeMonitoring `$false 已执行" 'Green'
} catch {
    Say "  设置失败：$($_.Exception.Message)" 'Yellow'
}
try {
    Set-MpPreference -DisableBehaviorMonitoring $false -ErrorAction SilentlyContinue
    Set-MpPreference -DisableIOAVProtection $false -ErrorAction SilentlyContinue
} catch {}

# ---------- 3. 排除项 ----------
Say ""
Say "== 3. 加排除项 =="
$root = Split-Path -Parent $PSScriptRoot
$yfRoot = Join-Path (Split-Path -Parent $root) 'YF-Robot'

$targets = @()
if (Test-Path $yfRoot) { $targets += $yfRoot }
$py = Join-Path $yfRoot 'runtime\python\python.exe'
if (Test-Path $py) { $targets += $py }
if (Test-Path $root) { $targets += $root }
foreach ($c in @(
    'C:\Program Files\Tencent\Weixin',
    (Join-Path $env:USERPROFILE 'Documents\WeChat Files'),
    (Join-Path $env:USERPROFILE 'Documents\xwechat_files')
)) {
    if ($c -and (Test-Path $c)) { $targets += $c }
}
$targets = $targets | Sort-Object -Unique

$addedOk = 0
$addFail = 0
try {
    $have = @((Get-MpPreference).ExclusionPath)
} catch {
    $have = @()
    Say "  读取现有排除项失败：$($_.Exception.Message)" 'Yellow'
}
foreach ($t in $targets) {
    if ($have -contains $t) { Say "  已存在：$t"; continue }
    try {
        Add-MpPreference -ExclusionPath $t -ErrorAction Stop
        Say "  已加入：$t" 'Green'
        $addedOk++
    } catch {
        Say "  加入失败：$t（$($_.Exception.Message)）" 'Yellow'
        $addFail++
    }
}
try {
    Add-MpPreference -ExclusionProcess 'python.exe' -ErrorAction Stop
    Say "  已加入进程：python.exe" 'Green'
} catch {}

# ---------- 4. 当前状态 ----------
Say ""
Say "== 4. 当前状态 =="
try {
    $st = Get-MpComputerStatus
    Say "  病毒防护启用: $($st.AntivirusEnabled)"
    Say "  实时保护启用: $($st.RealTimeProtectionEnabled)"
    Say "  特征库版本:   $($st.AntivirusSignatureVersion)"
    Say "  特征更新时间: $($st.AntivirusSignatureLastUpdated)"
} catch {
    Say "  读不到状态：$($_.Exception.Message)" 'Yellow'
}
try {
    $ex = (Get-MpPreference).ExclusionPath
    Say "  排除项数量: $(@($ex).Count)"
    $ex | ForEach-Object { Say "    $_" }
} catch {}

# ---------- 5. 还有个坑：假的 Reason 记录 ----------
Say ""
Say "== 5. 安全中心里的 Reason 残留 =="
try {
    $av = Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntiVirusProduct -ErrorAction Stop |
        Where-Object { $_.displayName -notmatch 'Windows Defender' }
    if ($av) {
        foreach ($a in $av) {
            $exe = $a.pathToSignedProductExe
            $exists = $false
            try { $exists = Test-Path $exe } catch {}
            Say "  $($a.displayName) → $exe （文件存在: $exists）" 'Yellow'
            if (-not $exists) {
                Say "    这是卸载残留：文件不存在，但安全中心还记着它。" 'Yellow'
                Say "    它会让系统以为有第三方杀软，从而不显示 Defender 的开关。" 'Yellow'
                Say "    要彻底清掉需要改安全中心的注册记录（风险低但不是必须），可另行处理。" 'Yellow'
            }
        }
    } else {
        Say "  没有第三方杀软记录"
    }
} catch {}

# ---------- 6. 写日志 ----------
Say ""
Say "==============================================" 'Cyan'
Say "  完成" 'Cyan'
Say "==============================================" 'Cyan'
$logPath = Join-Path $root 'def-recover.log'
try {
    Set-Content -Path $logPath -Value $log -Encoding UTF8
    Write-Host "  日志：$logPath" -ForegroundColor Cyan
} catch {
    Write-Host "  写日志失败：$($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  下一步：关掉适配器 → 普通双击 启动桥接.bat（不要用管理员）"
Read-Host "按回车退出"
