"""给白名单脚本加日志，方便事后核实（我不提权也能读）。"""
import io

P = "tools/whitelist-av.ps1"
s = io.open(P, encoding="utf-8-sig").read()

if "av-whitelist.log" in s:
    print("已存在")
    raise SystemExit(0)

anchor = '''# ---------- 5. 汇总 ----------'''
new = '''# ---------- 5. 写日志（不提权也能读，方便事后核查）----------
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

# ---------- 6. 汇总 ----------'''

if anchor not in s:
    print("找不到汇总锚点")
    raise SystemExit(1)

s = s.replace(anchor, new, 1)
# 保持 BOM + CRLF
io.open(P, "w", encoding="utf-8-sig", newline="\r\n").write(s)
print("已加日志输出")
