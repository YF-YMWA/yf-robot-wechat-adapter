"""改进白名单脚本：
  1. 微信目录查找加注册表兜底（进程 Path 常读不到）
  2. Defender 被第三方接管时，说清楚该去哪儿加，而不是只说「失败」
"""
import io

P = "tools/whitelist-av.ps1"
s = io.open(P, encoding="utf-8-sig").read()

# ---------- 1. 微信目录：注册表兜底 ----------
old_wx = '''$wxPaths = $wxPaths | Sort-Object -Unique

if ($wxPaths.Count -eq 0) {'''
new_wx = '''# 进程路径常常读不到（权限不足），注册表兜底
foreach ($k in @(
    'HKCU:\\Software\\Tencent\\Weixin',
    'HKCU:\\Software\\Tencent\\WeChat',
    'HKLM:\\SOFTWARE\\WOW6432Node\\Tencent\\Weixin',
    'HKLM:\\SOFTWARE\\WOW6432Node\\Tencent\\WeChat',
    'HKLM:\\SOFTWARE\\Tencent\\Weixin'
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
    "$env:ProgramFiles\\Tencent\\Weixin",
    "$env:ProgramFiles\\Tencent\\WeChat",
    "${env:ProgramFiles(x86)}\\Tencent\\WeChat",
    "$env:ProgramFiles\\Weixin"
)) {
    if ($c -and (Test-Path $c)) { $wxPaths += $c }
}

$wxPaths = $wxPaths | Sort-Object -Unique

if ($wxPaths.Count -eq 0) {'''
assert old_wx in s
s = s.replace(old_wx, new_wx, 1)

# ---------- 2. Defender 失败时给明确去向 ----------
old_err = '''} catch {
    Write-Host "  读不到 Defender 设置：$($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "  可能是第三方安全软件接管了，见下面手动步骤。"
}'''
new_err = '''} catch {
    Write-Host "  读不到 Defender 设置：$($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "  常见原因：第三方安全软件接管了 Defender（它变成被动模式，排除项由第三方管）" -ForegroundColor Yellow
    Write-Host "  → 这种情况不用管 Defender，直接在第三方软件里加白，见下面「第三方安全软件」一节"
}'''
assert old_err in s
s = s.replace(old_err, new_err, 1)

io.open(P, "w", encoding="utf-8-sig", newline="").write(s)
print("已改进：微信目录注册表兜底 + Defender 失败说明")
