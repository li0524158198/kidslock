# 儿童锁屏 · iOS 版（SwiftUI）

由 Android 原生版（https://github.com/wplleo/kidslock）移植的 iPhone/iPad 应用。

## 功能（与 Android 版一致）

- **定时锁屏**：15/30/45/60/90/120 分钟六档可选，到时自动锁屏
- **认字解锁**：答对五年级水平汉字拼音（144 字题库），连续答对 3/5/10 题解锁
- **家长PIN**：4 位 PIN 码快速解锁（默认 1234，连续错 5 次锁 30 秒）
- **状态持久化**：锁屏/计时状态保存在 UserDefaults，杀掉 App 重开依然有效

### iOS 平台差异说明

Android 版针对小米电视做了 HOME 键拦截、悬浮窗覆盖、开机自启等防绕过机制。
iOS 沙盒机制不允许任何 App 拦截 Home 手势或覆盖其他应用，因此 iOS 版的对应实现为：

| Android 版机制 | iOS 版实现 |
|---|---|
| 开机自启恢复 | 重新打开 App 自动恢复计时/锁屏状态 |
| 悬浮窗覆盖 + HOME 拦截 | 全屏锁屏界面 + 禁用返回/切换；到点发本地通知提醒 |
| 重启仍锁 | 状态持久化，重开 App 即锁屏 |

真正强制性的「孩子模式」在 iOS 上只有「屏幕使用时间」（系统自带，需家长密码）或 MDM 监管设备才能实现，任何第三方 App 都做不到。

## 如何编译

### 方式一：Mac + Xcode（推荐）

1. 把 `KidsLock` 文件夹拷到 Mac
2. 双击 `KidsLock/KidsLock.xcodeproj` 用 Xcode 打开（Xcode 15+）
3. 顶部选择你的开发团队（Signing & Capabilities → Team）
4. 数据线连接 iPhone，选择设备后按 ⌘R 运行

> 免费 Apple ID 也能真机运行（7 天签名有效期）；上架 App Store 需付费开发者账号（$99/年）。

### 方式二：GitHub Actions 云编译（无需 Mac）

1. 把本目录（含 `.github/workflows/build-ios.yml`）推到 GitHub 仓库
2. 仓库页面 → Actions → **Build iOS App** → Run workflow
3. 约 10 分钟后下载 Artifacts：
   - `KidsLock-simulator.app.zip`：iPhone 模拟器版
   - `KidsLock-unsigned.ipa`：未签名包，用 [AltStore](https://altstore.io) / Sideloadly 自签安装到真机

## 使用流程

1. 打开 App → 设置观看时长（默认 30 分钟）和解锁题数（默认 3 题）
2. 点「开始计时」，可退出 App（到点会收到本地通知）
3. 重新打开 App 或时间到 → 自动进入锁屏界面
4. 孩子连续答对指定题数的汉字拼音即可解锁
5. 家长点「家长解锁」输入 PIN（默认 1234，建议修改）

## 项目结构

```
KidsLock/
├── KidsLock.xcodeproj        # Xcode 工程
└── KidsLock/
    ├── KidsLockApp.swift     # 入口 + 根视图（锁屏/设置切换）
    ├── SettingsView.swift    # 设置主界面
    ├── LockScreenView.swift  # 锁屏认字界面
    ├── PinPadView.swift      # 家长PIN键盘
    ├── Prefs.swift           # 持久化状态管理（UserDefaults）
    ├── CharacterBank.swift   # 五年级汉字题库（144字）
    ├── Theme.swift           # 主题色（与 Android 版一致）
    └── Assets.xcassets       # 图标资源
```
