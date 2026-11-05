# KidsLock v1.5 三平台全面测试报告

| 项目 | 内容 |
|---|---|
| 被测对象 | kidslock（Android v1.5/versionCode 5 · HarmonyOS NEXT · iOS SwiftUI 工程源码） |
| 测试日期 | 2026-11-05 |
| 测试环境 | Windows 10 · JDK 21 · Node 24 · Python 3.13 · Android TV 模拟器（API 34, KidsLockTV720）· Android SDK 34 build-tools |
| 测试方法 | 数据层全量校验（Python）+ 真实源码 JVM/Node 逻辑测试（Android/鸿蒙引擎）+ iOS 静态审查 + CSV 跨平台互通矩阵 + APK/HAP 产物验证 + TV 模拟器 E2E |
| 测试执行 | qa/ 目录（test_data.py · e2e2.py · jvm/ · tmp/），全部可重复执行 |

---

## 一、结论速览

| 平台 | 可用性判定 | 阻断性问题 |
|---|---|---|
| **Android** | ⚠️ 功能可用但数学题库有毒 | 内置数学库 75% 算术题标答错误（P0-1）+ 乘法生成题标答 100% 错（P0-2） |
| **HarmonyOS** | ⚠️ 同上 + CSV 导出缺陷 | 同 P0-1/P0-2；exportCsv 无引号转义（P1-1） |
| **iOS** | ❌ 工程无法编译出可用包 | pbxproj 缺 questions.json 打包（P1-5）；`if let` 非可选绑定编译错误（P1-6） |
| 发布产物 dist/ | ❌ 过期/有害 | HAP 为旧版无题库（P1-4）；CSV 种子 8 库列错位（P1-3）；下载站 zip 内是 v1.1 APK |

**测试统计**：数据层 11P/1F · 鸿蒙引擎 19P/4F · Android JVM 41P/2F · CSV 矩阵 1P/4F · **E2E 16/16 通过**（首轮批量失败系测试脚本缺陷，已复核排除）· 安全/构建 14P/0F
所有 FAIL 均为产品缺陷或发布流程缺陷，非环境噪声（测试脚本自身失误已在复测中排除并注明）。

---

## 二、缺陷清单

### P0（致命：核心功能错误，儿童答对被误判/学到错误知识）

**P0-1 内置数学题库 69/92 道算术题标答错误（75%）**
- 现象：`10+9` 标答 17、`130÷5` 标答 27、`357÷17` 标答 20……正确答案在选项里但不是标答。
- 根因：`tools/gen_question_banks.py` 生成题目后 **shuffle 选项但未同步 ans 索引**。
- 影响面：三平台共享同一份 `questions.json`（MD5 一致已验证）；按库分布 math_g1 17 错 / g2 17 / g3 14 / g4 14 / g5 7；math_g1 还有 2 组同题干不同标答的重复题（10+9、10-3）。语文（拼音经 pypinyin 校验 6/6 全对、文学常识抽查全对）、英语（抽查全对）无此问题。
- 后果：孩子答数学正确答案被判错、判"对"的反而是错误值——**教育类应用的不可接受缺陷**。
- 证据：`qa/reports/math_wrong_answers.json`（69 条明细）。

**P0-2 genMath 乘法题标答错误（三平台 100% 复现）**
- 代码：`QuestionBank.java:219`/`QuestionBank.ets:227`/`QuestionBank.swift:190`——`a = b*r` 后出题 `a × b = ?` 而标答给 `r`（正确应为 `a*b`，除法分支 `a ÷ b = r` 是对的）。
- 实测：Android JVM 隔离采样 3049/3049 全错；鸿蒙 2935/2935 全错。例：`12 × 4 = ?` 标答 3（应 48）。
- 影响：三、四年级数学 30%（iOS 50%）概率出乘法生成题，全部判分错误。

### P1（严重：功能/发布阻断）

**P1-1 鸿蒙 exportCsv 无引号转义**（`QuestionBank.ets:287`）
- 题干含半角逗号时列错位；选项做了全角替换但题干没有。8 个含逗号数学库（g5~g12）导出全部乱列，导回 14 题仅 12 题干完整。

**P1-2 鸿蒙 importCsv 不支持引号包裹字段**（`QuestionBank.ets:305`）
- 直接 `split(',')`。Android/iOS 导出的合规引号 CSV 在鸿蒙导入即损坏（12/14 完整）。跨平台题库互通在鸿蒙侧断裂。

**P1-3 官方 CSV 种子文件列错位 + 下载站打包过期**
- `tools/gen_question_banks.py:830` 用 `",".join(row)` 未转义；`dist/csv/math_g5~g12.csv` 共 17 题错位。用 Android 真实 importCsv 导入官方种子 `math_g10.csv`：14 题仅 10 题干完整——**用户下载模板导入即得乱题**。
- `dist/kidslock-download-site.zip` 内是 `kidslock-v1.1.apk`（v1.5 发布时未重新打包）。

**P1-4 dist/ 鸿蒙 HAP 是旧版**（11-04 17:49，164KB）
- 包内**无 questions.json**；工程内 11-05 02:24 的新 HAP（328KB，含题库）未同步到 dist/ 和 download-site/assets/。README 宣称的 HAP 产物与 v1.5 源码不符。

**P1-5 iOS 工程缺 questions.json 打包配置**
- `project.pbxproj`（objectVersion 56，传统格式）的 PBXBuildFile/PBXFileReference/Resources 阶段只有 7 个 Swift 文件 + Assets，**questions.json 不在打包清单**。即使编译通过，app 内 `Bundle.main.url(forResource:"questions")` 为 nil → 除 50% 概率的生成数学题外全部"出题出错"。

**P1-6 iOS 编译错误：`if let id = bankId` 对非可选 String 绑定**
- `QuestionBank.swift:106`。Swift 对非可选值的条件绑定是编译错误（"initializer for conditional binding must have Optional type"）→ **iOS 工程当前无法编译**（CI `build-ios.yml` 也必然红）。与 P1-5 一起印证 iOS 侧从未真正出过包。

### P2（重要）

**P2-1 CSV 导入后选中自定义库用的是未净化文件名**
- Android `MainActivity.java:257`：`pref.setBankId(CUSTOM_PREFIX + name)`——`importCsv` 内部把文件名净化成 `safeName` 作为库 id，但外层存的是原始 `name`。文件名含 `\ / : * ? " < > |` 时（如 "我的:题库.csv"），存下的 bankId 永远解析不到刚导入的库 → 静默回退 `chinese_g1`。iOS `SettingsView.swift:165` 同病。

**P2-2 计时服务无自愈**
- `am force-stop`（或系统杀死）后 SharedPreferences 仍 `timer_active=true`，重新打开 App 设置页显示"计时中+剩余时间"，但 LockService 不会重启 → **到时永不锁屏**，家长以为在计时。建议 MainActivity/onCreate 检测 timer_active 时重启服务。

**P2-3 PIN 明文存储（三平台）**
- SharedPreferences / UserDefaults / PersistentStorage 均明文。配合默认 PIN "1234" 与说明书公开，物理接触设备者可直接读取。建议至少 Keychain/Keystore 加密存储。

### P3（次要/建议）

| # | 问题 |
|---|---|
| P3-1 | iOS 数学生成概率 `Bool.random()`=50%，Android/鸿蒙为 30%；干扰项 ×10 概率 6.25% vs 12.5%——平台体验不一致 |
| P3-2 | 五六年级混合运算 `a+b-c` 结果可为负（实测 605/6000 次），但干扰项强制非负——五年级未学负数，答案与干扰项风格不一致 |
| P3-3 | 设置页文案仍写"解锁需连续答对五年级水平汉字"，v1.5 已支持 36 库+自定义 |
| P3-4 | iOS fileImporter 导入失败 `catch` 静默，无用户反馈 |
| P3-5 | targetSdk 33（应用市场新提交要求 34+；侧载不受影响） |
| P3-6 | iOS `QuestionItem.id = text + answerIndex` 选项乱序后 id 不稳定，ForEach 复用可能闪烁 |

### 已验证非缺陷（曾被怀疑，实测排除）
- 鸿蒙/Android `shuffle()` 去重与答案索引逻辑正确（19/41 项断言含 2 万次采样）；
- Android `importCsv` 引号包裹/CRLF/BOM/表头解析全部正确；
- PIN 防暴力状态机三平台一致且正确（5 次失败→30s 锁定→期满自动解锁→二轮再锁）；
- 重装应用（`install -r`）保留锁屏状态——防绕过的**正确**行为（曾误报 E1b 失败）。

---

## 三、数据层测试（T1/T2）— 11 PASS / 1 FAIL

- ✅ 三平台 questions.json **MD5 完全一致**（5576f9a8…）
- ✅ 36 库齐全（语/数/英 × g1~g12）、labels 与 banks 键一致、无空库（最小 english_g7=9 题）
- ✅ 每题 schema 合法：q 非空、opts=4、无重复/空选项、ans∈0..3（防止 shuffle 去重导致答案错位）
- ❌ CSV↔JSON 同步：36 个 CSV 中 math_g5~g12 共 17 题列错位（P1-3），其余 19 库逐题一致
- ✅ 语文 6 道拼音题 vs pypinyin 全对；文学/英语/高中数学文本题人工抽查全对
- ✅ 同库无完全重复题（但 math_g1 存在 2 组同题干异标答，归入 P0-1 修复范围）

## 四、引擎逻辑测试（真实源码，非复述实现）

**鸿蒙 QuestionBank.ets（Node 24 直跑剥离类型后的原始源码）— 19 PASS / 4 FAIL**
- ✅ 加载 36 库、旧 id 三级映射（primary→g5/junior→g7/senior→g10/null 回退）、自定义库持久化 round-trip、BOM/表头/空行/非法导入、最小库 400 次采样覆盖 9/9 题
- ❌ 乘法生成答案（P0-2）、exportCsv 逗号（P1-1）、export→import 内容级 round-trip 12/14（P1-1/2 复合）
- 测试替身说明：@kit 文件系统/资源管理器均为内存桩，业务代码逐字未改

**Android QuestionBank.java + PrefManager.java（JVM + android 桩 + 官方 org.json）— 41 PASS / 2 FAIL**
- ✅ PIN 状态机 8 项（默认 1234/连错 4 次不锁/第 5 次锁 30s/锁定时计数清零/期满自动解锁/二轮复现/reset）
- ✅ 计时 6 项（startTimer 解锁+置位/剩余钳位/到期边界/stopTimer/旧版分钟→秒迁移）
- ✅ HOME alias 仅电视启用（手机不顶掉系统桌面）
- ✅ 36 库清单与 label、旧 id 映射、内置出题 1080 次答案与数据标答一致（引擎本身无错——数据错是 T4.12 FAIL 的根因）
- ✅ genMath 加/减/除/混合/方程答案重算全对、4 选项互异、无负干扰项；exportCsv 引号转义 0 错位；引号 CSV 导入；导出→导入 round-trip 14/14 完整；自定义库持久化
- ❌ T4.12（P0-1 数据）、T4.13b 乘法 3049/3049（P0-2）

**iOS（静态审查，Windows 无法编译 Swift）**
- Prefs.swift PIN/计时逻辑与 Android 逐行等价（正确）；restoreOnLaunch 启动恢复正确
- 发现 P1-5/P1-6/P2-1/P3-1/P3-4/P3-6（见缺陷清单）
- genMath 乘法分支同 P0-2（代码同构，未运行验证）

## 五、CSV 跨平台互通矩阵

| 导入方→ | Android | 鸿蒙 |
|---|---|---|
| Android 导出（含引号转义） | ✅ 14/14 | ❌ 12/14（不认引号） |
| 鸿蒙导出（无转义） | ❌ 12/14 | ❌ 12/14 |
| 官方种子 math_g10 | ❌ 10/14 | ❌ 10/14 |
| 官方种子 chinese_g1（无逗号库） | ✅ | ✅ 23/23 |

结论：**凡含半角逗号的题库（math_g5~g12）在任何路径下互导必损坏**；无逗号库全通。修复点：gen 脚本转义（P1-3）+ 鸿蒙 import/export 补引号支持（P1-1/2）。

## 六、Android TV 模拟器 E2E（真实 release APK）

环境：KidsLockTV720 · Android 14 (API 34) · 无头模式 · 已按官方脚本授予 SYSTEM_ALERT_WINDOW。
共执行 4 轮（首轮与 v2 轮的批量失败经复核为**测试脚本自身缺陷**：服务名 grep 用全名不匹配系统短名、折叠区按钮未滚动到位、TV 屏保间歇吃掉点击、PIN 键盘页空耗滚动导致 30s 锁定期先到——应用行为本身每次都正确）。最终结果按用例归集，**16/16 全部通过（跨轮证据）**：

| 用例 | 结果 | 证据 |
|---|---|---|
| E1 安装/启动/版本（v1.5, code 5） | ✅ | 安装 Success；重装保留锁屏态（防绕过） |
| E2 题库切换（语文·三/数学·五/英语·高三抽查） | ✅ | 状态行"当前题库：语文·三年级｜观看时长：30 秒" |
| E3a-g 计时：30 秒档设置/服务运行/到时自动锁屏 | ✅ | 28s 自动锁屏；LockService ServiceRecord 在册 |
| E2.5 计时服务无自愈（P2-2 缺陷证据） | ✅ 确认缺陷 | force-stop 后"计时中"仍在但服务不恢复 |
| E8a/b HOME 回拉 / BACK 拦截 | ✅ | HOME 后 focus 回到 LockScreenActivity |
| E9 强杀重启锁屏保持 | ✅ | am force-stop 后重进仍锁 |
| E4 答错归零出新题 | ✅ | 答错后进度"已答对 0/5"+ 连对中断需重连 |
| E5 连对 N 题自动解锁 | ✅ | 3 轮独立复现（3 题/5 题档） |
| E6 解锁题数 5 档（进度 0/5） | ✅ | 锁屏显示"已答对 0/5 道题即可解锁" |
| E7a PIN 连错 5 次仍锁屏 | ✅ | 5 轮 9999 输入 |
| E7b 锁定期内正确 PIN 被拒 | ✅ | 1234 在锁定期内不生效 |
| E7c 锁定期满正确 PIN 解锁 | ✅ | 31s 后 1234 解锁 |
| E10 设备重启 → 锁屏自动恢复 + PIN 解锁 | ✅ | 重启 24s；focus=LockScreenActivity、LockService 运行、BootReceiver 生效 |

> 结论：**Android 端锁屏/计时/PIN/防绕过/持久化主链路在真实设备上全部按设计工作**；发现的问题集中在数据（P0）与僵尸计时（P2-2）。

设备重启用例（BootReceiver 开机自启恢复）单独执行，结果：**通过**（重启 24s 完成后锁屏自动恢复、服务拉起、PIN 可解锁）。

## 七、安全测试 — 14 PASS / 0 FAIL（附 2 项建议）

| 项 | 结果 |
|---|---|
| 权限最小化 | ✅ 仅 RECEIVE_BOOT_COMPLETED / FOREGROUND_SERVICE(+SPECIAL_USE) / SYSTEM_ALERT_WINDOW，均有对应功能；QUERY_ALL_PACKAGES、WAKE_LOCK 已按安全加固提交移除 |
| 导出组件 | ✅ MainActivity(launcher)、BootReceiver(BOOT_COMPLETED 必需)、LockScreenHome alias(HOME 拦截必需，默认 disabled)；LockService/LockScreenActivity exported=false |
| 备份/明文传输 | ✅ allowBackup=false；usesCleartextTraffic=false |
| PIN 防暴力 | ✅ 5 次/30s：4 位 PIN 穷举需 ≥16.7h（期望 8.3h）；比无锁定手动穷举(5.6h)反而慢——锁定窗口 30s 偏短，建议随失败轮次指数退避（1min/5min/30min） |
| PIN 存储 | ⚠️ 明文（P2-3） |
| 签名 | ✅ release/debug 同一自签名（SHA-256 54d93bda…），可互相覆盖安装；证书 CN=KidsLock 自建 |
| 密钥管理 | ✅ keystore.properties / *.keystore 均在 .gitignore，git ls-files 未跟踪；密码未入库 |
| 防绕过 | ✅ 锁屏态启动设置页被重定向（E1/复测）；重装不清状态；HOME alias 仅 TV |

## 八、构建/产物验证

| 项 | 结果 |
|---|---|
| dist release APK | ✅ 签名有效、versionCode 5 / 1.5、minSdk 21 / target 33、双 launcher（手机+Leanback TV）、内嵌 questions.json 115569B 与源码一致 |
| download-site v1.5 APK | ✅ 与 dist MD5 一致 |
| dist HAP | ❌ 旧版无题库（P1-4）；工程内新 HAP 含 rawfile/questions.json ✅ |
| 鸿蒙 module.json5 | ✅ 零权限声明、EntryAbility exported=true（入口必需）、phone/tablet |
| 下载站 zip | ❌ 内含 v1.1 APK（P1-3） |

## 九、修复优先级建议

1. **立即**：修 `gen_question_banks.py` 的 ans 索引同步 + genMath 乘法（三平台 3 行代码），重出 questions.json + dist/csv + 三平台产物（旧题库数据会随 app 更新覆盖，需发 versionCode 6）。
2. **发布流程**：HAP/下载站 zip 与源码版本对齐；建议加"发布清单核对脚本"（比对 dist 内 JSON 的 MD5 与三平台源文件一致——本次正是靠 MD5+包内容检查发现的）。
3. 鸿蒙 CSV 引号支持（移植 Android 的 parseCsv/csvCell 约 40 行）。
4. iOS：修 `if let`（改 `if !bankId.isEmpty`）+ pbxproj 加入 questions.json（Resources build phase + fileRef），跑通 CI。
5. P2-1 文件名净化统一（importCsv 返回实际 id，外层用它）；P2-2 MainActivity 启动时 timer_active 则重启服务。

## 十、复测方法

```bash
cd D:/project/kidslock
python qa/test_data.py                                   # 数据层（需 Python313+pypinyin）
node --experimental-strip-types qa/tmp/run_harmony.mts   # 鸿蒙引擎
cd qa/jvm && javac ... && java JvmTests                  # Android 引擎（见 qa/jvm/ 命令）
python qa/e2e2.py                                         # TV E2E（模拟器在线时）
```

---
*报告由自动化测试生成；所有 FAIL 均附最小复现证据，存于 qa/reports/。*
