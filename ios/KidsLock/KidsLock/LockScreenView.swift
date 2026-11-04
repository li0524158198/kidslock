import SwiftUI

/// 锁屏界面：按所选题库（人教版语数英，1-12 年级 / 自定义 CSV）出题。
/// - 语文拼音题显示大字；其他题型显示题干（自适应字号）
/// - 答错重置计数
/// - 家长可通过输入 PIN 码强制解锁
struct LockScreenView: View {
    @EnvironmentObject var prefs: Prefs

    // 题目状态
    @State private var questionText = ""
    @State private var bigChar: String? = nil
    @State private var bankLabel = ""
    @State private var options: [String] = ["", "", "", ""]
    @State private var answerIndex = 0
    @State private var correctCount = 0
    @State private var answerLocked = false
    @State private var selectedIndex: Int? = nil
    @State private var wasCorrect = false
    @State private var feedbackShown = false

    // PIN 界面
    @State private var showPinPad = false

    private var requiredCount: Int { prefs.unlockCount }

    var body: some View {
        VStack(spacing: 12) {
            if showPinPad {
                PinPadView(
                    prefs: prefs,
                    onBack: {
                        withAnimation { showPinPad = false }
                    },
                    onUnlocked: unlock
                )
            } else {
                quizView
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Theme.bgDark.ignoresSafeArea())
        .onAppear { loadNextQuestion() }
    }

    // MARK: - 答题视图

    private var quizView: some View {
        VStack(spacing: 12) {
            Text("屏幕已锁定")
                .font(.headline)
                .foregroundColor(Theme.textSecondary)
                .padding(.top, 8)

            Text(bankLabel)
                .font(.subheadline)
                .foregroundColor(Theme.highlight)

            // 大字（仅字音题）或题干（自适应字号）
            if let ch = bigChar {
                Text(ch)
                    .font(.system(size: 120, weight: .bold))
                    .foregroundColor(Theme.accent)
                    .minimumScaleFactor(0.5)
                    .lineLimit(1)
            }
            Text(questionText)
                .font(.title3)
                .foregroundColor(Theme.textPrimary)
                .multilineTextAlignment(.center)
                .lineLimit(4)
                .minimumScaleFactor(0.5)
                .padding(.horizontal, 24)
                .frame(minHeight: 48)

            Text("已答对 \(correctCount)/\(requiredCount) 道题即可解锁")
                .font(.subheadline)
                .foregroundColor(Theme.textSecondary)

            Text(feedbackText)
                .font(.headline)
                .foregroundColor(feedbackShown ? (wasCorrect ? Theme.correctGreen : Theme.wrongRed) : .clear)
                .frame(height: 28)

            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                ForEach(Array(options.enumerated()), id: \.offset) { idx, option in
                    optionButton(index: idx, text: option)
                }
            }
            .padding(.horizontal, 24)

            Button {
                withAnimation { showPinPad = true }
            } label: {
                Text("家长解锁")
                    .font(.subheadline)
                    .foregroundColor(Theme.highlight)
                    .underline()
            }
            .padding(.bottom, 12)
        }
    }

    private func optionButton(index: Int, text: String) -> some View {
        let state = buttonState(for: index)
        return Button {
            onOptionSelected(index)
        } label: {
            Text(text)
                .font(.body.weight(.medium))
                .lineLimit(2)
                .minimumScaleFactor(0.5)
                .multilineTextAlignment(.center)
                .frame(maxWidth: .infinity, minHeight: 52)
                .padding(.horizontal, 8)
                .background(
                    RoundedRectangle(cornerRadius: 10)
                        .fill(state.background)
                        .overlay(
                            RoundedRectangle(cornerRadius: 10)
                                .strokeBorder(state.border, lineWidth: state.borderWidth)
                        )
                )
                .foregroundColor(state.foreground)
        }
        .disabled(answerLocked)
    }

    private func buttonState(for index: Int) -> (background: Color, foreground: Color, border: Color, borderWidth: CGFloat) {
        guard answerLocked, selectedIndex != nil else {
            return (Theme.bgSurface, Theme.textPrimary, Theme.primary, 1)
        }
        if index == selectedIndex {
            return wasCorrect
                ? (Theme.correctGreen, .white, Theme.correctGreen, 0)
                : (Theme.wrongRed, .white, Theme.wrongRed, 0)
        }
        if !wasCorrect && options.indices.contains(index) && index == answerIndex {
            return (Theme.correctGreen.opacity(0.25), Theme.correctGreen, Theme.correctGreen, 1)
        }
        return (Theme.bgSurface.opacity(0.5), Theme.textSecondary, Theme.primary.opacity(0.5), 1)
    }

    private var feedbackText: String {
        wasCorrect ? "答对了！" : "答错了，重新开始！"
    }

    // MARK: - 出题

    private func loadNextQuestion() {
        let bankId = prefs.bankId
        bankLabel = QuestionBank.shared.label(bankId)
        let q = QuestionBank.shared.getQuestion(bankId)
        questionText = q.text
        bigChar = q.bigChar
        options = q.options
        answerIndex = q.answerIndex
        selectedIndex = nil
        answerLocked = false
        feedbackShown = false
    }

    private func onOptionSelected(_ index: Int) {
        guard !answerLocked, options.indices.contains(index) else { return }
        answerLocked = true
        selectedIndex = index

        if index == answerIndex {
            wasCorrect = true
            feedbackShown = true
            correctCount += 1
            if correctCount >= requiredCount {
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) { unlock() }
            } else {
                DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) { loadNextQuestion() }
            }
        } else {
            wasCorrect = false
            feedbackShown = true
            correctCount = 0
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) { loadNextQuestion() }
        }
    }

    // MARK: - 解锁

    private func unlock() {
        prefs.unlockAll()
    }
}
