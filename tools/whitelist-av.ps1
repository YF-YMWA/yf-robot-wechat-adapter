# 加入杀毒软件白名单
#
# 为什么需要：微信自动化要读微信进程的模块、给窗口发按键。
# 部分安全软件会拦「模块枚举 / 进程读取」，表现就是适配器日志里
# 「控件树拿不到」「落点窗口不属于微信」，语音/发消息都不稳。
#
# 本脚本做三件事：
#   1. 把 python.exe、程序目录、适配器目录、微信目录加进 Windows Defender 排除项
#   2. 找出微信进程的真实安装目录和数据目录（自动，不用你手抄）
#   3. 如果装了第三方安全软件（Reason / 360 / 火绒 …），打印手动加白的路径

$ErrorActionPreference = 'Continue'

function Test-Admin {
    $p = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Admin)) {
    Write-Host "[X] 需要管理员权限。请右键这个脚本 -> 以管理员身份运行，" -ForegroundColor Red
    Write-Host "    或双击同目录的「加入杀软白名单.bat」（它会自己申请提权）。"
    Read-Host "按回车退出"
    exit 1
}

Write-Host "=============================================="
Write-Host "  加入杀毒软件白名单"
Write-Host "=============================================="
Write-Host ""

# ---------- 1. 收集要排除的路径 ----------
$root = Split-Path -Parent $PSScriptRoot          # 适配器目录
$yfRoot = Join-Path (Split-Path -Parent $root) 'YF-Robot'

$paths = @()
if (Test-Path $yfRoot) { $paths += $yfRoot }
if (Test-Path $root) { $paths += $root }

# python.exe（框架自带的运行时 + 系统里所有 python）
$py1 = Join-Path $yfRoot 'runtime\python\python.exe'
if (Test-Path $py1) { $paths += $py1 }
Get-Command python.exe -ErrorAction SilentlyContinue | ForEach-Object { $paths += $_.Source }
Get-Command py.exe -ErrorAction SilentlyContinue | ForEach-Object { $paths += $_.Source }

# ---------- 2. 找微信目录 ----------
Write-Host "== 找微信目录 =="
$wxPaths = @()

# 先用 CIM 拿可执行文件路径（实测比 Get-Process.Path 可靠，普通权限也能读）
foreach ($pn in @('Weixin.exe', 'WeChat.exe')) {
    try {
        Get-CimInstance Win32_Process -Filter "Name='$pn'" -ErrorAction SilentlyContinue |
            ForEach-Object {
                if ($_.ExecutablePath) { $wxPaths += (Split-Path -Parent $_.ExecutablePath) }
            }
    } catch {}
}

foreach ($name in @('Weixin', 'WeChat')) {
    Get-Process -Name $name -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            if ($_.Path) {
                $wxPaths += (Split-Path -Parent $_.Path)
            }
        } catch {}
    }
}
$wxPaths = $wxPaths | Sort-Object -Unique

# 微信数据目录（4.x 是 xwechat_files，3.x 是 WeChat Files）
foreach ($base in @("$env:USERPROFILE\Documents", "$env:USERPROFILE\Documents\WeChat Files")) {
    foreach ($n in @('xwechat_files', 'WeChat Files')) {
        $c = Join-Path $base $n
        if (Test-Path $c) { $wxPaths += $c }
    }
}
$drive = $env:SystemDrive
foreach ($n in @('xwechat_files', 'WeChat Files')) {
    $c = Join-Path $drive "$n"
    if (Test-Path $c) { $wxPaths += $c }
}
# 进程路径常常读不到（权限不足），注册表兜底
foreach ($k in @(
    'HKCU:\Software\Tencent\Weixin',
    'HKCU:\Software\Tencent\WeChat',
    'HKLM:\SOFTWARE\WOW6432Node\Tencent\Weixin',
    'HKLM:\SOFTWARE\WOW6432Node\Tencent\WeChat',
    'HKLM:\SOFTWARE\Tencent\Weixin'
)) {
    try {
        $item = Get-ItemProperty -Path $k -ErrorAction Stop
        foreach ($field in @('InstallPath', 'InstallDir', 'FileSavePath', 'Executable')) {
            $v = $item.$field
            if ($v -and (Test-Path $v)) {
                if (Test-Path (Join-Path $v 'Weixin.exe') -ErrorAction SilentlyContinue) { $wxPaths += $v }
                elseif ((Get-Item $v).PSIsContainer) { $wxPaths += $v }
            }
        }
    } catch {}
}

# 常见安装位置兜底
foreach ($c in @(
    "$env:ProgramFiles\Tencent\Weixin",
    "$env:ProgramFiles\Tencent\WeChat",
    "${env:ProgramFiles(x86)}\Tencent\WeChat",
    "$env:ProgramFiles\Weixin"
)) {
    if ($c -and (Test-Path $c)) { $wxPaths += $c }
}

$wxPaths = $wxPaths | Sort-Object -Unique

if ($wxPaths.Count -eq 0) {
    Write-Host "  没找到微信目录（微信没开？可以先打开微信再跑一次）" -ForegroundColor Yellow
} else {
    $wxPaths | ForEach-Object { Write-Host "  $_" }
}

# 已知安装位置（自动探测读不到时兜底）
$known = @(
    'C:\Program Files\Tencent\Weixin',
    'C:\Program Files\Tencent\WeChat',
    (Join-Path $env:USERPROFILE 'Documents\xwechat_files'),
    (Join-Path $env:USERPROFILE 'Documents\WeChat Files')
)
foreach ($c in $known) {
    if ($c -and (Test-Path $c)) { $wxPaths += $c }
}
$wxPaths = $wxPaths | Sort-Object -Unique

$all = @($paths + $wxPaths) | Where-Object { $_ -and (Test-Path $_) } | Sort-Object -Unique

# ---------- 3. 加进 Defender 排除项 ----------
Write-Host ""
Write-Host "== Windows Defender 排除项 =="
$defenderOk = $false
try {
    $pref = Get-MpPreference -ErrorAction Stop
    $have = @($pref.ExclusionPath)
    foreach ($p in $all) {
        if ($have -contains $p) {
            Write-Host "  已存在：$p"
            continue
        }
        try {
            Add-MpPreference -ExclusionPath $p -ErrorAction Stop
            Write-Host "  已加入：$p" -ForegroundColor Green
        } catch {
            Write-Host "  加入失败：$p（$($_.Exception.Message)）" -ForegroundColor Yellow
        }
    }
    # 进程名也加一次（按进程名排除，路径变了也管用）
    try {
        Add-MpPreference -ExclusionProcess 'python.exe' -ErrorAction Stop
        Write-Host "  已加入进程：python.exe" -ForegroundColor Green
    } catch {}

    $defenderOk = $true
} catch {
    Write-Host "  读不到 Defender 设置：$($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "  常见原因：第三方安全软件接管了 Defender（它变成被动模式，排除项由第三方管）" -ForegroundColor Yellow
    Write-Host "  → 这种情况不用管 Defender，直接在第三方软件里加白，见下面「第三方安全软件」一节"
}

if ($defenderOk) {
    Write-Host ""
    Write-Host "  当前排除项：" -ForegroundColor Cyan
    try {
        (Get-MpPreference).ExclusionPath | ForEach-Object { Write-Host "    $_" }
    } catch {}
}

# ---------- 4. 第三方安全软件：给手动步骤 ----------
Write-Host ""
Write-Host "== 第三方安全软件 =="
$avs = @()
try {
    $avs = Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntiVirusProduct -ErrorAction Stop |
        Where-Object { $_.displayName -notmatch 'Windows Defender' }
} catch {}

if ($avs.Count -eq 0) {
    Write-Host "  没检测到第三方杀毒软件（只有 Defender 就够了）"
} else {
    foreach ($av in $avs) {
        Write-Host "  检测到：$($av.displayName)" -ForegroundColor Yellow
        $n = $av.displayName
        if ($n -match 'Reason|Cylance') {
            Write-Host "    路径：打开 Reason 客户端 -> 设置/Settings -> 排除项/Exclusions -> 添加文件夹"
        } elseif ($n -match '360') {
            Write-Host "    路径：360 安全卫士 -> 木马查杀 -> 信任区 -> 添加目录"
        } elseif ($n -match '火绒|Huorong') {
            Write-Host "    路径：火绒 -> 防护中心 -> 信任区 -> 添加目录"
        } elseif ($n -match '腾讯|QQ|Tencent') {
            Write-Host "    路径：腾讯电脑管家 -> 设置 -> 白名单 -> 添加目录"
        } elseif ($n -match 'Kaspersky') {
            Write-Host "    路径：卡巴斯基 -> 设置 -> 安全 -> 排除项 -> 添加文件夹"
        } else {
            Write-Host "    在它的「白名单 / 信任区 / 排除项」里添加下面这些路径"
        }
        Write-Host "    要加的路径："
        $all | ForEach-Object { Write-Host "      $_" }
    }
}

# ---------- 5. 写日志（不提权也能读，方便事后核查）----------
$logPath = Join-Path (Split-Path -Parent $PSScriptRoot) 'av-whitelist.log'
try {
    $lines = @()
    $lines += "时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    $lines += "管理员: 是"
    $lines += "Defender 处理成功: $defenderOk"
    $lines += "路径清单:"
    $all | ForEach-Object { $lines += "  $_" }
    $lines += "第三方安全软件:"
    if ($avs.Count -eq 0) { $lines += "  （无）" } else { $avs | ForEach-Object { $lines += "  $($_.displayName)" } }
    $lines += "当前 Defender 排除项:"
    try { (Get-MpPreference).ExclusionPath | ForEach-Object { $lines += "  $_" } } catch { $lines += "  （读取失败）" }
    Set-Content -Path $logPath -Value $lines -Encoding UTF8
    Write-Host ""
    Write-Host "  日志已写入：$logPath" -ForegroundColor Cyan
} catch {
    Write-Host "  写日志失败：$($_.Exception.Message)" -ForegroundColor Yellow
}

# ---------- 6. 汇总 ----------
Write-Host ""
Write-Host "=============================================="
Write-Host "  汇总"
Write-Host "=============================================="
Write-Host "  处理了 $($all.Count) 个路径："
$all | ForEach-Object { Write-Host "    $_" }
Write-Host ""
Write-Host "  加完后请："
Write-Host "    1. 关掉适配器窗口，重新双击 启动桥接.bat"
Write-Host "    2. 跑 语音自检.bat，看「控件树拿不到」是否消失"
Write-Host ""
Read-Host "按回车退出"
