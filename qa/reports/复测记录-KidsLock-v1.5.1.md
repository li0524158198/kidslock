# KidsLock v1.5.1 修复复测记录

- 修复日期：2026-11-05
- 对照文档：`qa/reports/测试报告-KidsLock-v1.5.md`（v1.5 全面测试报告）
- 修复范围：P0-1/P0-2、P1-1~P1-6、P2-1/P2-2、P3-1~P3-6（P2-3 PIN 加密存储经确认不在本轮范围）
- 发布版本：Android versionCode 6 / versionName 1.5.1 / targetSdk 34；鸿蒙 versionCode 1000001 / versionName 1.0.1

## 一、缺陷修复对照

| 编号 | 修复内容 | 验证结果 |
|---|---|---|
| P0-1 | `gen_question_banks.py` shuffle 后同步 ans 索引 + 同库题干去重；重出三平台 questions.json | 69 条错误明细全部修正（10+9→19、10-3→7）；算术题重算 88 道 0 错；重复题干 0 组 |
| P0-2 | 三平台 genMath 乘法分支标答 `r`→`a*b` | Android JVM 2985 采样 0 错；鸿蒙 3600 采样 0 错 |
| P1-1 | 鸿蒙 exportCsv 移植 csvCell 引号包裹 | T3.8 含逗号 8 库列完整（引号外逗号=6） |
| P1-2 | 鸿蒙 importCsv 移植 parseCsv 状态机（引号/转义/BOM） | M1 Android 引号导出→鸿蒙导入 14/14 |
| P1-3 | gen 脚本 CSV 用 csv.writer 转义；下载站 zip 重打（v1.1→v1.5.1 APK） | T2.2 36 库 CSV↔JSON 逐题一致；M5 官方种子导入 14/14；R6 zip 内 APK 与 dist 一致 |
| P1-4 | 新 HAP（332KB，含题库，1.0.1）同步 dist/ 与 download-site/assets/ | R4 HAP 内嵌 questions.json MD5 与源码一致 |
| P1-5 | pbxproj 加入 questions.json（FileRef+BuildFile+Group+Resources 四处） | 静态核查（Windows 无法编译 Swift，CI 待推送验证） |
| P1-6 | `resolveBankId` 去掉对非可选 String 的 `if let` 绑定 | 静态核查 |
| P2-1 | 三平台 importCsv 改为返回净化后的库 id，外层用它选中题库（新增 bankSize 取题数） | T3.6a/T4.15a 等断言通过 |
| P2-2 | MainActivity onCreate 检测 timer_active 重启 LockService | TV 模拟器定向冒烟：force-stop 后重开 App 服务自愈、倒计时连续（见下） |
| P3-1 | iOS 生成概率 50%→30%、干扰项×10 6.25%→12.5%；鸿蒙 ×10 10%→12.5% | 代码对齐 Android 基准（静态核查） |
| P3-2 | 三平台混合运算 c 上限 min(40, a+b-1)，结果恒 ≥1 | T4.13e INFO 负数答案 0 次 |
| P3-3 | 设置页文案改"解锁需连续答对所选题库的题目" | 模拟器 dump 确认新文案渲染 |
| P3-4 | iOS fileImporter catch 改为 alert 展示错误 | 静态核查 |
| P3-5 | targetSdk 33→34（manifest 已有 specialUse FGS 声明） | aapt 确认 targetSdk=34，安装启动正常 |
| P3-6 | iOS QuestionItem.id 改 text+options.joined()（内容稳定） | 静态核查 |

## 二、复测结果汇总

| 套件 | v1.5 基线 | v1.5.1 复测 |
|---|---|---|
| 数据层 qa/test_data.py | 11P/1F | **12P/0F** |
| 鸿蒙引擎 qa/tmp/run_harmony.mts | 19P/4F | **23P/0F** |
| Android JVM qa/jvm | 41P/2F | **43P/0F** |
| CSV 跨平台矩阵 | 1P/4F | **5P/0F**（M1~M5） |
| 发布核对 tools/release_check.py | — | **7P/0F**（新增脚本） |
| TV E2E qa/e2e2.py | 16/16（跨轮） | 脚本受 TV 焦点恢复影响按钮定位不稳定（与 v1.5 首轮同类脚本缺陷）；改用定向冒烟覆盖关键链路 |

TV 模拟器定向冒烟（emulator-5554，真实 release APK v1.5.1）：
- 安装 versionCode 6 / 1.5.1 ✓；启动正常 ✓
- 30 秒计时启动 → LockService 运行 ✓
- am force-stop 后重开 App → **服务自愈重启、剩余时间连续**（P2-2 修复生效）✓
- 到时自动锁屏 → 出题正常 → PIN 1234 解锁回桌面 ✓

## 三、QA 资产同步说明

- `qa/tmp/run_harmony.mts`、`qa/tmp/QuestionBank.ts`、`qa/tmp/run_csv_matrix.mts` 内嵌的引擎副本已同步为修复后源码（副本与 `.ets` 保持逐行一致的原则不变）
- `qa/jvm/src/JvmTests.java`、`CsvMatrix.java`：importCsv 返回值断言改为 `bankSize(importCsv(...))` 适配新 API
- 已知脚本问题（与 v1.5 报告备注一致）：e2e2.py 在 TV 焦点恢复后滚动定位不稳定，建议后续固定"先回顶部再定位"策略（本次定向冒烟即采用该策略）

## 四、复测命令

```bash
cd D:/project/kidslock
python qa/test_data.py
node --experimental-strip-types qa/tmp/run_harmony.mts
node --experimental-strip-types qa/tmp/run_csv_matrix.mts   # 需先跑 Android 侧导出
cd qa/jvm && java -cp "out;../../qa/tmp/org.json.jar" CsvMatrix   # javac 见本次执行记录
python tools/release_check.py
python qa/auto_continue_smoke.py                             # 自动继续闭环（需模拟器在线）
```

## 五、追加缺陷修复（同日第二轮，用户报告）

**P2-4 解锁后不再自动锁屏（三平台逻辑缺陷）**
- 现象：开机自动计时 → 到点锁屏 → 孩子答题解锁后 `timer_active=false` 且无人重启 → 之后再也不会自动锁屏，直到下次设备重启。"自动继续"只保护开机后的第一轮。
- 根因：三平台解锁（Android `unlock()` / iOS·鸿蒙 `unlockAll()`）一律 `stopTimer()`；autoStart 仅在 BootReceiver/启动恢复时触发一次。
- 修复（三平台对称，语义：孩子答题解锁 ≠ 家长接管）：
  - **答题解锁**且"自动继续"开启 → 立即 `startTimer(watchLimitSeconds)` 开始下一轮（看 N 分钟 → 答题 → 再看 N 分钟循环）；关闭则维持停止。
  - **家长 PIN 解锁** → 保持完全停止（家长接管）。
  - Android：`LockScreenActivity.unlockByQuiz()`（新）+ `LockService` 竞态修复——watchdog 解锁时若新计时已激活则切回计时模式而非 `stopSelf()`（旧逻辑会在 800ms 内自杀并吞掉重启请求）；`startTicking()` 幂等化；设置页"开机自启"更名"自动继续"（对齐鸿蒙/iOS 命名与新语义）。
  - 鸿蒙 `Lock.ets` / iOS `LockScreenView.swift`：新增 `unlockByQuiz()`，答题路径改调之。
- 真机闭环冒烟 `qa/auto_continue_smoke.py`（6/6 PASS）：立即锁屏 → 自动连对 3 题解锁（脚本从 questions.json/表达式重算标答，顺带真机验证题库修复）→ 解锁后服务自动切换计时模式 + 状态"计时中" → 30 秒后**再次自动锁屏** → PIN 解锁后"未计时"（家长接管语义保持）。
- 产物已重新构建同步（APK 4787422B / HAP 333520B），`tools/release_check.py` 7/7。

## 六、追加缺陷修复（同日第三轮，用户报告）

**P1-7 语数英学科选择无效（三平台）+ 设置页缺版本显示**
- 现象（Android 最重）：点"数学/英语"学科按钮只改内存变量，不切换题库、不更新状态行；高亮基于已保存 bankId 计算，点了"数学"高亮仍停在"语文"、年级高亮全部消失——用户视角"点了没反应"。年级按钮点击后也不刷新高亮；toast 文案写死"语文/数学/英语 · N 年级"。
- 鸿蒙/iOS 同构问题：点学科不设置 bankId；鸿蒙重进设置页学科高亮还不同步（currentSubject 恒从 0 开始）。
- 修复（三平台统一语义：**点学科 = 保留当前年级、立即切换题库并更新状态/高亮/toast**）：
  - Android `MainActivity`：学科点击 `setBankId(subject + "_g" + savedGrade())` + `updateStatus()` + `refreshBankSelection()`；年级点击补 `refreshBankSelection()`；toast 改为真实库名（`getLabel()`）；新增 `savedGrade()`。
  - 鸿蒙 `Index.ets`：学科点击切库 + toast 库名；`aboutToAppear` 新增 `syncSubjectFromBank()` 同步学科高亮；新增 `savedGrade()`。
  - iOS `SettingsView`：学科点击切库；`onAppear` 同步 `currentSubject`；新增 `savedGrade()`。
- **iOS 连带发现第二个编译缺陷**（报告 P1-6 之外）：`QuestionBank.swift` 缺 `builtinId`/`builtinLabel` 静态方法但 SettingsView 在调用（从未编译的又一证据）——已补齐（与鸿蒙同名方法对齐）。
- **版本显示**：三平台设置页标题下显示版本号（Android `PackageManager` 读 versionName；鸿蒙 `bundleManager.getBundleInfoForSelfSync`；iOS `CFBundleShortVersionString`）。
- 真机冒烟 `qa/bank_switch_smoke.py`（5/5 PASS）：版本显示 v1.5.1 ✓；点数学→"数学·五年级"（保留年级）✓；点英语→"英语·五年级" ✓；点"三"→"英语·三年级"（年级联动）✓。
- 产物重新构建同步（APK 4787766B / HAP 339532B），`tools/release_check.py` 7/7。

## 七、模拟器全量回归（同日，v1.5.1 release APK 部署 emulator-5554）

修复 `qa/e2e2.py` 五处历史脚本缺陷后，TV 全量 E2E **18/18 PASS**（`qa/reports/e2e2_v151_final.log`）：
1. dump 陈旧文件：toast 显示期间 `uiautomator dump` 静默失败残留旧文件 → 先 `rm` 再 dump 并校验输出重试；
2. `tap_text` 交替 ±1 屏滚动永远到不了页面顶部按钮 → 改"先滚回顶部再逐屏向下"；
3. `status_line` 误匹配"导出当前题库 CSV"按钮 → 收紧为"当前题库："并优先题库行；
4. E7b 的 `tap_text('家长解锁')` 在键盘页徒劳搜索 30~40 秒，把 30 秒 PIN 锁定期耗光导致误报 → 键盘页直接输入；
5. E4 解锁后 `finishAffinity` 回桌面未重新拉起设置页 → 补 `ensure_unlocked()`；另支持字音题/生成数学题识别。

| 用例组 | 结果 |
|---|---|
| E1 启动/锁屏态恢复 | ✅ |
| E2 题库切换 ×3（语文·三/数学·五/英语·高三，本轮修复点） | ✅ 3/3 |
| E2.5 计时自愈（P2-2 修复点：force-stop 后服务自愈、剩余 29:46 连续） | ✅ |
| E3 30 秒档→服务运行→28s 自动锁屏 | ✅ |
| E8 HOME 回拉 / BACK 拦截 | ✅ |
| E9 锁屏态强杀保持 | ✅ |
| E4 答错归零出新题 | ✅ |
| E5 连对 5 题自动解锁 | ✅ |
| E6 解锁题数 5 档 | ✅ |
| E7 PIN 防暴力（5 错锁定/期内拒绝/期满解锁） | ✅ 3/3 |

配套冒烟（同 APK）：自动继续闭环 `auto_continue_smoke.py` 6/6、学科切换 `bank_switch_smoke.py` 5/5。
