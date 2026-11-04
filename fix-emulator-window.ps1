# 强制把指定 AVD 的模拟器窗口移到屏幕内指定位置
# 用法: powershell -File fix-emulator-window.ps1 -AvdName KidsLock [-X 20] [-Y 20]
param(
  [string]$AvdName = "KidsLock",
  [int]$X = 20,
  [int]$Y = 20
)
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class W32Fix {
  [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr h, int x, int y, int w, int ht, bool repaint);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  public struct RECT { public int L, T, R, B; }
}
"@
$q = Get-Process qemu-system-x86_64 -ErrorAction SilentlyContinue |
  Where-Object { $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -like "*$AvdName*" } |
  Select-Object -First 1
if ($q) {
  $r = New-Object W32Fix+RECT
  [W32Fix]::GetWindowRect($q.MainWindowHandle, [ref]$r) | Out-Null
  $w = $r.R - $r.L; $ht = $r.B - $r.T
  [W32Fix]::MoveWindow($q.MainWindowHandle, $X, $Y, $w, $ht, $true) | Out-Null
  Start-Sleep -Milliseconds 200
  $r2 = New-Object W32Fix+RECT
  [W32Fix]::GetWindowRect($q.MainWindowHandle, [ref]$r2) | Out-Null
  Write-Output ("moved ({0},{1}) size {2}x{3}" -f $r2.L, $r2.T, ($r2.R-$r2.L), ($r2.B-$r2.T))
} else {
  Write-Output "no-window"
}
