import SwiftUI

/// 家长PIN码输入界面：4位数字键盘 + 防暴力锁定。
struct PinPadView: View {
    @ObservedObject var prefs: Prefs
    let onBack: () -> Void
    let onUnlocked: () -> Void

    @State private var pinInput = ""
    @State private var message = ""
    @State private var messageColor: Color = Theme.wrongRed
    @State private var checkTask: DispatchWorkItem?

    var body: some View {
        VStack(spacing: 20) {
            Text("请输入家长PIN码")
                .font(.headline)
                .foregroundColor(Theme.textSecondary)
                .padding(.top, 30)

            // PIN 显示：● ● ● ●
            HStack(spacing: 16) {
                ForEach(0..<4, id: \.self) { i in
                    Image(systemName: i < pinInput.count ? "circle.fill" : "circle")
                        .font(.system(size: 22))
                        .foregroundColor(Theme.accent)
                }
            }

            Text(message)
                .font(.subheadline)
                .foregroundColor(messageColor)
                .frame(height: 20)

            // 数字键盘 3x4
            LazyVGrid(columns: Array(repeating: GridItem(.flexible()), count: 3), spacing: 14) {
                ForEach(1...9, id: \.self) { digit in
                    padButton(digit.description) { tapDigit(digit) }
                }
                padButton("清除") {
                    pinInput = ""
                }
                padButton("0") { tapDigit(0) }
                padButton("返回", color: Theme.highlight) { onBack() }
            }
            .padding(.horizontal, 40)

            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func padButton(_ title: String, color: Color = Theme.textPrimary, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(title)
                .font(.title3.weight(.medium))
                .frame(maxWidth: .infinity)
                .padding(.vertical, 14)
                .background(
                    RoundedRectangle(cornerRadius: 10)
                        .fill(Theme.bgSurface)
                        .overlay(RoundedRectangle(cornerRadius: 10).strokeBorder(Theme.primary))
                )
                .foregroundColor(color)
        }
    }

    private func tapDigit(_ digit: Int) {
        guard pinInput.count < 4 else { return }
        pinInput.append(Character(String(digit)))
        if pinInput.count == 4 {
            checkTask?.cancel()
            let task = DispatchWorkItem { checkPin() }
            checkTask = task
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.2, execute: task)
        }
    }

    private func checkPin() {
        if prefs.isPinLocked {
            let remainingSec = Int(prefs.pinLockRemainingMillis / 1000)
            message = "尝试次数过多，请 \(remainingSec) 秒后再试"
            messageColor = Theme.warningOrange
            pinInput = ""
            return
        }
        if prefs.checkPin(pinInput) {
            prefs.resetPinFailures()
            onUnlocked()
        } else {
            prefs.recordPinFailure()
            message = "PIN码错误"
            messageColor = Theme.wrongRed
            pinInput = ""
        }
    }
}
