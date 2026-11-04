# 儿童锁屏 · 鸿蒙 HarmonyOS 版（ArkTS）

由 Android 原生版（https://github.com/wplleo/kidslock）移植的鸿蒙应用（Stage 模型 / ArkTS / API 12）。

## 功能（与 Android 版一致）

- **定时锁屏**：15/30/45/60/90/120 分钟六档可选，到时自动锁屏
- **认字解锁**：答对五年级水平汉字拼音（144 字题库），连续答对 3/5/10 题解锁
- **家长PIN**：4 位 PIN 码快速解锁（默认 1234，连续错 5 次锁 30 秒）
- **状态持久化**：锁屏/计时状态通过 PersistentStorage 持久化，杀掉应用重开依然有效
- **防绕过**：锁屏页拦截返回键；从桌面图标重开应用时若处于锁屏状态直接进入锁屏页

### 鸿蒙平台差异说明

Android TV 版做了 HOME 键拦截（launcher alias）、全局悬浮窗覆盖、开机广播自启。
鸿蒙系统不允许普通应用替换桌面/拦截 Home 手势/开机自启（需系统级权限），因此鸿蒙版的对应实现为：

| Android 版机制 | 鸿蒙版实现 |
|---|---|
| 开机自启恢复 | 打开应用自动恢复计时/锁屏状态 |
| HOME 拦截 + 悬浮窗覆盖 | 全屏锁屏页 + 拦截返回键 |
| 重启仍锁 | PersistentStorage 持久化 |

## 如何编译

### 方式一：DevEco Studio（推荐）

1. 安装 [DevEco Studio 5.0+](https://developer.huawei.com/consumer/cn/deveco-studio/)（自带 HarmonyOS SDK）
2. 打开本目录：`File → Open → 选择 KidsLock 文件夹`
3. 首次打开会自动 sync；如提示安装 SDK，按提示安装 API 12+
4. 真机运行：`File → Project Structure → Signing Configs` 勾选 **Automatically generate signature**（需华为开发者账号，免费注册）
5. 手机开启开发者模式（设置→关于→连点版本号；USB 连接后在开发者选项打开 USB 调试），点 Run ▶️

### 方式二：命令行（hvigor，已在 Windows 上实测通过）

需要：Node.js 18+、OpenHarmony 5.0.3 SDK（约 4.5GB）、hvigor 5.7.0

```bash
# 1. 下载 SDK（华为云镜像）
curl -O https://repo.huaweicloud.com/openharmony/os/5.0.3-Release/ohos-sdk-windows_linux-public.tar.gz

# 2. 解压 windows 目录下的 5 个组件 zip（ets/js/native/previewer/toolchains）

# 3. 组装为 hvigor 认可的 SDK 结构（DevEco 风格）：
#    <SDK根>/toolchains/sdk-pkg.json          （组件清单元数据，apiVersion=12, platformVersion=5.0.0）
#    <SDK根>/toolchains/openharmony/<组件>/    （真实 SDK 组件，含 oh-uni-package.json + uni-package.json）
#    <SDK根>/toolchains/hms/<组件>/            （指向 openharmony 组件，id_defined.json 需为空表）
#    详细做法见本仓库 tools/setup-ohos-sdk 说明或 build-ohos.bat

# 4. 安装 hvigor（华为 npm 镜像，本工程内已装好）
npm config set registry https://repo.harmonyos.com/npm
npm install @ohos/hvigor@5.7.0 @ohos/hvigor-ohos-plugin@5.7.0

# 5. 编译
export DEVECO_SDK_HOME=/path/to/sdk
node node_modules/@ohos/hvigor/bin/hvigor.js assembleHap --mode module -p product=default --no-daemon
# 产物：entry/build/default/outputs/default/entry-default-unsigned.hap
```

> 编译产物为**未签名 HAP**。安装到鸿蒙手机需要签名：
> 在 DevEco Studio 中用 Automatic Signature 自动签名后重新出包，或参考
> [HarmonyOS 应用签名指南](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/ide-signing) 配置证书。

## 使用流程

1. 打开应用 → 设置观看时长（默认 30 分钟）和解锁题数（默认 3 题）
2. 点「开始计时」，可以退出应用
3. 时间到 → 重新打开应用即进入锁屏界面
4. 孩子连续答对指定题数的汉字拼音即可解锁
5. 家长点「家长解锁」输入 PIN（默认 1234，建议修改）

## 项目结构

```
KidsLock/
├── AppScope/                      # 应用级配置与资源
│   ├── app.json5                  # bundleName: com.kidslock.harmony
│   └── resources/base/...
├── build-profile.json5            # 工程构建配置（API 5.0.3(12)）
├── hvigorfile.ts                  # hvigor 构建脚本
├── entry/                         # 主模块
│   ├── src/main/
│   │   ├── module.json5           # 模块清单（入口 Ability、页面路由）
│   │   ├── ets/
│   │   │   ├── entryability/EntryAbility.ets   # 入口（锁屏状态开屏直达锁屏页）
│   │   │   ├── model/AppInit.ets               # 持久化状态管理
│   │   │   ├── model/CharacterBank.ets         # 五年级汉字题库（144字）
│   │   │   └── pages/
│   │   │       ├── Index.ets     # 设置页
│   │   │       └── Lock.ets      # 锁屏认字页（拦截返回键）
│   │   └── resources/base/       # 颜色、字符串、图标
│   └── build-profile.json5
└── oh-package.json5
```

## 兼容性

- 目标：HarmonyOS NEXT 5.0（API 12）及以上，同时兼容 HarmonyOS 5.1 / 6.x
- 设备：phone / tablet
- 另注：HarmonyOS 4.x 及更早版本（兼容 Android APK 的版本）可直接安装 Android 版 APK，无需本工程
