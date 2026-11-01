"""兜底：把已知微信安装位置直接写进白名单清单。"""
import io

P = "tools/whitelist-av.ps1"
s = io.open(P, encoding="utf-8-sig").read()

if "已知安装位置" in s:
    print("已存在")
    raise SystemExit(0)

anchor = "$all = @($paths + $wxPaths)"
add = r'''# 已知安装位置（自动探测读不到时兜底）
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

'''

if anchor not in s:
    print("找不到锚点")
    raise SystemExit(1)

s = s.replace(anchor, add + anchor, 1)
io.open(P, "w", encoding="utf-8-sig", newline="").write(s)

# 统一 BOM + CRLF
p = io.open(P, encoding="utf-8-sig").read()
io.open(P, "wb").write(b"\xef\xbb\xbf" + p.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8"))
print("已加兜底路径")
