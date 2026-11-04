# KidsLock 三平台构建总览

原始项目：[wplleo/kidslock](https://github.com/wplleo/kidslock)（Android 原生 · 小米电视儿童锁屏）

本目录包含三个平台的版本（均已按各自平台的标准工程结构移植/编译）：

| 目录 | 平台 | 技术栈 | 构建结果 |
|---|---|---|---|
| `kidslock-src/` | Android 5.0+（手机/电视） | Java + Gradle（原版工程） | ✅ 已本地编译出签名 APK |
| `harmony/KidsLock/` | 鸿蒙 HarmonyOS NEXT 5.0+（API 12） | ArkTS（Stage 模型） | ✅ 已本地编译出 HAP（未签名） |
| `ios/KidsLock/` | iPhone / iPad（iOS 16+） | SwiftUI | 📦 完整 Xcode 工程（Windows 无法编译 iOS，见下方说明） |

## 产物（dist/）

```
dist/
├── kidslock-release-universal.apk   # Android 通用版（已签名，可直接安装；覆盖 armeabi-v7a/arm64-v8a）
├── kidslock-debug-universal.apk     # Android 调试版
└── entry-default-unsigned.hap       # 鸿蒙 HAP（未签名，需 DevEco Studio 自动签名后安装）
```

> iOS 受苹果许可限制，IPA 只能在 macOS + Xcode（或 GitHub Actions 的 macOS Runner）上编译。
> `ios/README.md` 提供两种方式，其中 GitHub Actions 云编译**无需 Mac**，约 10 分钟出包。

## 应用功能（三平台一致）

- **定时锁屏**：15/30/45/60/90/120 分钟六档，到时自动锁屏
- **认字解锁**：144 个五年级汉字，4 选 1 拼音，连续答对 3/5/10 题解锁（答错重置）
- **家长 PIN**：默认 1234，连错 5 次锁 30 秒
- **状态持久化**：锁屏/计时状态重启不丢

### 平台差异说明（安全模型不同，无法 1:1 移植的部分）

| Android 电视版机制 | 鸿蒙/iOS 版等价实现 |
|---|---|
| 开机自启（BOOT_COMPLETED） | 打开应用自动恢复计时/锁屏状态 |
| HOME 键拦截（launcher alias） | 全屏锁屏页 + 拦截返回键（系统不允许第三方拦截 Home） |
| 全局悬浮窗覆盖桌面 | 应用内锁屏 + 状态持久化（iOS 另有到点本地通知） |

## 各平台构建方法

### Android（本机已构建成功）

```bash
cd kidslock-src
# 需要 JDK 17+（本机用了 C:\java\jdk-21.0.7）、Android SDK 34
gradle assembleDebug assembleRelease
# 产物：app/build/outputs/apk/
```

本机做的适配：AGP 8.2.0→8.2.2（修复 JDK 21 jlink 兼容）、release 签名改为读取本地
`kidslock-src/keystore.properties`（不入库，参照 `keystore.properties.example` 自行配置）、
Gradle/Maven 换国内镜像。

**手机/平板适配**（原版仅按电视布局设计，在手机上会溢出截断）：
- `values/dimens.xml` 默认改为紧凑尺寸；`values-sw600dp/dimens.xml` 保留原电视尺寸（大屏自动切换）
- 设置页三组按钮改为 GridLayout：计时控制 2×2、观看时长 3×2、解锁题数 1×3，小屏自动换行
- 锁屏认字页包 ScrollView 兜底；手机上不强制横屏（电视仍横屏）
- HOME launcher alias 防绕过仅在电视设备启用（手机上启用会顶掉系统桌面且无效果）
- 已在手机模拟器（Pixel 6 / Android 14）实测：设置页/锁屏/PIN 解锁全流程无截断

### 鸿蒙（本机已构建成功）

```bash
cd harmony/KidsLock
set DEVECO_SDK_HOME=<组装好的SDK根目录>   # 组装方法见 tools/setup-ohos-sdk.py 或 harmony/README.md
node node_modules/@ohos/hvigor/bin/hvigor.js assembleHap --mode module -p product=default --no-daemon
```

用 OpenHarmony 5.0.3 SDK + hvigor 5.7.0 实测编译通过。该工程也可直接用
DevEco Studio 5.0+ 打开（推荐，自动签名后即可安装到鸿蒙手机）。

### iOS（需 Mac 或 CI）

- Mac：Xcode 15+ 打开 `ios/KidsLock/KidsLock.xcodeproj`，选团队后 ⌘R
- 无 Mac：把 `ios/` 推到 GitHub，手动触发 Actions 里的 **Build iOS App** 工作流，下载 Artifact

## 目录结构

```
kidslock/
├── kidslock-src/          # Android 原版工程（含构建产物）
├── harmony/
│   ├── KidsLock/          # 鸿蒙 ArkTS 工程
│   ├── build-ohos.bat     # 命令行编译脚本
│   └── README.md
├── ios/
│   ├── KidsLock/          # SwiftUI Xcode 工程
│   ├── .github/workflows/ # GitHub Actions 云编译工作流
│   └── README.md
├── tools/                 # 本机构建环境（JDK/Android SDK/OpenHarmony SDK/hvigor）
├── dist/                  # 最终产物
└── README.md
```
