# TV 遥控器（D-pad）专项测试记录

日期：2026-11-05 · 设备：KidsLockTV720 模拟器（Android 14 / API 34）· 对象：dist v1.5.1（19:36 构建，1141 题版）
方法：**全程仅用遥控按键**（DPAD 方向/确认/ENTER/HOME/BACK/数字/菜单键），无触屏点击——模拟真实电视无触屏交互。脚本：`qa/tv_remote_test2.py` / `qa/tv_remote_test4.py`（坐标引导焦点导航）。

## 结果：11 PASS / 0 FAIL

| 用例 | 结果 | 说明 |
|---|---|---|
| T1 Leanback 启动器入口启动 | ✅ | TV 桌面图标路径可用 |
| T1b 遥控全键盘 PIN 解锁 | ✅ | D-pad 导航屏上数字键盘逐位输入 |
| T2a 设置页 D-pad 焦点遍历 | ✅ | 12 个焦点站（计时/学科/年级/时长/题数/PIN 全可达），无焦点死区 |
| T2b 遥控「立即锁屏」+ 确认键 | ✅ | 焦点引导 + DPAD_CENTER 触发锁屏 |
| T3a 遥控答错归零出新题 | ✅ | 进度归零 0/3 |
| T3b 遥控连对 3 题自动解锁 | ✅ | 纯遥控作答 4 次完成解锁 |
| T4a HOME 后确认键回锁屏 | ✅ | 悬浮窗拦截遥控确认键（dispatchKeyEvent: ENTER/CENTER/SPACE）|
| T4b ENTER 键回锁屏 | ✅ | 同上 |
| T5 锁屏页 BACK 无效 | ✅ | 拦截生效 |
| T6 杂项按键健壮性 | ✅ | MENU/音量/数字/彩色键连按无崩溃 |
| T7 HOME 回拉锁屏 | ✅ | HOME alias 生效（logcat 证实"儿童锁屏"已注册 HOME 类别）|

## 发现

### TV-1（P3，可用性建议）：PIN 键盘不响应遥控器物理数字键
- `LockScreenActivity` 的 PIN 输入只有屏上按钮 `OnClickListener`，没有 `onKeyDown`/`dispatchKeyEvent` 处理 `KEYCODE_0..9`（对比：`LockService.LockOverlayView` 就处理了遥控按键）。
- 后果：TV 上家长输 PIN 需用方向键在 3×4 键盘逐格导航，4 位数字约需 10+ 次按键，繁琐且易错。
- 建议：`LockScreenActivity` 增加 `onKeyDown` 把 `KEYCODE_0..9` 映射为 `onPinDigit(digit)`，一行分发即可，TV 体验大幅提升（手机行为不变）。

### 观察项
- "自动继续"开启时，答题解锁后 30 秒档立即重新计时并很快再锁——测试时易干扰流程（符合设计，非缺陷）；建议测试脚本注意或临时关闭自动继续。
- 早期遥控测试轮次的批量失败均为测试脚本自身问题（未回顶导航陷入 GridLayout 歧义、PIN 设置对话框污染焦点、题库映射未覆盖全库），已修正并在最终轮全部通过；期间误触打开的 PIN 设置对话框已将 PIN 重置回 1234。

## 顺带复核：发布核对全绿
本轮测试中 dist 产物被重新构建（19:36），复跑 `release_check.py`：**7 PASS / 0 FAIL**——上一轮报告的 N-1（APK/HAP 内嵌题库落后源码）**已修复**：APK 内嵌 1141 题与 `data/questions.json` 完全一致，下载站资产同步。
