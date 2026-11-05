# QA 测试资产

三平台 KidsLock 的全部回归资产。环境约定见 `qaenv.py`（仓库根自动推导，
可用 `KIDSLOCK_ADB` / `KIDSLOCK_SERIAL` 环境变量覆盖，换机器无需改代码）。

## 分层结构

| 层 | 入口 | 依赖 | 说明 |
|---|---|---|---|
| 数据层校验 | `python qa/test_data.py` | 无（离线） | 单一源 + 三平台 JSON 一致、36 库 schema、CSV 种子同步 |
| 题库/状态机逻辑回归 | `qa\jvm\run.bat`（Linux/macOS 用 `run.sh`） | JDK 8+ | Android **真实生产源码** + `jvm/shims` 里的 Android API 替身，桌面 JVM 直接跑 |
| 跨平台 CSV 矩阵 | `qa\jvm\run.bat csv` | JDK 8+ | Android 导入鸿蒙导出/官方种子的兼容性矩阵（M4 需鸿蒙侧导出，见下） |
| 设备冒烟（E2E） | `python qa/e2e_tv.py` 等 | 模拟器/真机 + adb | uiautomator 驱动的全流程实测 |
| 发布核对 | `python qa/release_check.py` | dist/ 产物齐全 | R1-R7：题库 MD5、APK/HAP 内嵌题库、下载站资产一致性 |

## 题库单一源（重要）

所有脚本读 `data/questions.json`（仓库唯一题库源）。改题库的正确流程：

```
1. python scripts/gen_question_banks.py   # 改生成器后重新生成（固定种子，可复现）
2. python scripts/sync_questions.py       # 分发到三平台资源位
3. python scripts/sync_questions.py --check && python qa/test_data.py   # 校验
```

**不要直接改三平台目录下的 questions.json**——`sync_questions.py --check` 和
`release_check.py` R1 都会拦。

## JVM 逻辑回归（无需设备）

```bash
# Windows
qa\jvm\run.bat

# Linux / macOS（shims 为纯 Java，无平台依赖）
qa/jvm/run.sh
```

编译对象 = `jvm/shims`（android.\* 替身）+ 生产源码 `PrefManager.java` / `QuestionBank.java`
+ `jvm/src` 测试。`jvm/vendor/org.json.jar` 为 org.json 官方 jar（编译期依赖）。
`CsvMatrix` 的 M4 用例需要 `qa/tmp/hm_export_math_g9.csv`（鸿蒙侧导出产物，scratch 不入库），
缺失时该用例记 SKIP 不算失败。

## 设备冒烟脚本一览（需要 adb + 在线模拟器/真机）

| 脚本 | 覆盖 |
|---|---|
| `full_regression.py [serial]` | Android 全功能回归（TV 模拟器） |
| `e2e_tv.py` | TV 全流程（真实 release APK 安装起测） |
| `e2e2.py` / `e2e3.py` | TV E2E 迭代版（滚动找按钮、僵尸计时验证） |
| `verify3.py` / `verify4.py` | 靶向复测（切库 / 答题 / PIN 锁定期） |
| `auto_continue_smoke.py` | 答题解锁→自动继续→再锁→PIN 解锁闭环 |
| `bank_switch_smoke.py` | 学科/年级切换 + 版本显示 |
| `reboot_test.py` | 设备重启 → BootReceiver 恢复锁屏 |
| `answer_quiz.py` | 答题辅助小工具（配合人工调试） |
| `dbg.py` | dump/tap/focus/logcat 交互调试 |

运行示例：

```bash
cd qa
python e2e_tv.py                          # 默认 emulator-5554
KIDSLOCK_SERIAL=emulator-5556 python full_regression.py   # 指定设备
```

## 测试报告

`reports/` 下是各版本的测试报告与复测记录（`.log` 为运行留档，不入库）。

## patches-archive

`jvm/patches-archive/` 是 v1.5 开发期的一次性补丁脚本归档，改动已体现在源码中，仅作追溯。
