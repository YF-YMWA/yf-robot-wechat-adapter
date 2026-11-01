# 修复 Windows Defender 服务
#
# 前一步 Set-MpPreference 报 0x800106ba —— 意思是 Defender 服务起不来。
# Reason 卸载后常把它禁用了。这一步：
#   1. 看 WinDefend / WdNisSvc / Sense 三个服务的状态与启动类型
#   2. 被禁用的改回「自动」并尝试启动
#   3. 清掉安全中心里那条指向不存在文件的 Reason 记录（让系统重新认 Defender）
#   4. 结果写 def-service.log

$ErrorActionPreference = 'Continue'

$p = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "[X] 需要管理员权限。请双击「修复防护服务.bat」。" -ForegroundColor Red
    Read-Host "按回车退出"
    exit 1
}

$log = New-Object System.Collections.ArrayList
function Say($m, $c = 'Gray') { Write-Host $m -ForegroundColor $c; [void]$log.Add($m) }

Say "==============================================" 'Cyan'
Say "  修复 Windows Defender 服务" 'Cyan'
Say "==============================================" 'Cyan'
Say ""

$names = @('WinDefend', 'WdNisSvc', 'Sense', 'SecurityHealthService', 'wscsvc')

Say "== 1. 服务现状 =="
foreach ($n in $names) {
    $svc = Get-Service -Name $n -ErrorAction SilentlyContinue
    if (-not $svc) { Say "  $n ：不存在" 'Yellow'; continue }
    $wmi = Get-CimInstance Win32_Service -Filter "Name='$n'" -ErrorAction SilentlyContinue
    Say ("  {0,-22} 状态={1,-8} 启动类型={2}" -f $n, $svc.Status, $wmi.StartMode)
}

Say ""
Say "== 2. 改回自动并启动 =="
foreach ($n in @('WinDefend', 'WdNisSvc')) {
    $svc = Get-Service -Name $n -ErrorAction SilentlyContinue
    if (-not $svc) { continue }
    try {
        Set-Service -Name $n -StartupType Automatic -ErrorAction Stop
        Say "  $n ：启动类型已改为 自动" 'Green'
    } catch {
        Say "  $n ：改启动类型失败（$($_.Exception.Message)）" 'Yellow'
    }
    try {
        Start-Service -Name $n -ErrorAction Stop
        Say "  $n ：已启动" 'Green'
    } catch {
        Say "  $n ：启动失败（$($_.Exception.Message)）" 'Yellow'
    }
}

Say ""
Say "== 3. 清掉安全中心里的假杀软记录 =="
$avKey = 'HKLM:\SOFTWARE\Microsoft\Windows Security Center\Provider\Av'
if (Test-Path $avKey) {
    Get-ChildItem $avKey -ErrorAction SilentlyContinue | ForEach-Object {
        $item = Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue
        $name = $item.DISPLAYNAME
        $exe = $item.ARTIFACTNAME
        $exists = $false
        try { if ($exe) { $exists = Test-Path $exe } } catch {}
        if ($name -and $name -notmatch 'Windows Defender' -and -not $exists) {
            Say "  删除残留记录：$name → $exe" 'Yellow'
            try {
                Remove-Item $_.PSPath -Recurse -Force -ErrorAction Stop
                Say "    已删除" 'Green'
            } catch {
                Say "    删除失败（$($_.Exception.Message)）" 'Yellow'
            }
        } else {
            Say "  保留：$name"
        }
    }
} else {
    Say "  没有安全中心 Av 记录"
}

Say ""
Say "== 4. 再试一次开启防护 =="
try {
    Set-MpPreference -DisableRealtimeMonitoring $false -ErrorAction Stop
    Say "  实时保护已请求开启" 'Green'
} catch {
    Say "  仍然失败：$($_.Exception.Message)" 'Yellow'
}
try {
    $st = Get-MpComputerStatus
    Say "  病毒防护: $($st.AntivirusEnabled) / 实时保护: $($st.RealTimeProtectionEnabled)"
    Say "  特征库: $($st.AntivirusSignatureVersion)"
} catch {
    Say "  读不到状态：$($_.Exception.Message)" 'Yellow'
}

Say ""
Say "== 5. 加排除项（服务正常时才有用）=="
$root = Split-Path -Parent $PSScriptRoot
$yfRoot = Join-Path (Split-Path -Parent $root) 'YF-Robot'
$targets = @($yfRoot, (Join-Path $yfRoot 'runtime\python\python.exe'), $root,
             'C:\Program Files\Tencent\Weixin',
             (Join-Path $env:USERPROFILE 'Documents\WeChat Files'))
$targets = $targets | Where-Object { $_ -and (Test-Path $_) } | Sort-Object -Unique
$okAdd = 0
foreach ($t in $targets) {
    try {
        Add-MpPreference -ExclusionPath $t -ErrorAction Stop
        Say "  已加入：$t" 'Green'; $okAdd++
    } catch {
        Say "  失败：$t" 'Yellow'
    }
}
Say "  成功 $okAdd / $($targets.Count)"

Say ""
Say "==============================================" 'Cyan'
Say "  完成" 'Cyan'
Say "==============================================" 'Cyan'
try {
    Set-Content -Path (Join-Path $root 'def-service.log') -Value $log -Encoding UTF8
    Write-Host "  日志：$(Join-Path $root 'def-service.log')" -ForegroundColor Cyan
} catch {}
Write-Host ""
Write-Host "  如果服务还是起不来，通常要重启一次电脑；还不行说明 Defender 被卸载坏了，"
Write-Host "  用「设置 → 应用 → 可选功能 → Windows 安全中心」修复，或 sfc /scannow。"
Read-Host "按回车退出"
