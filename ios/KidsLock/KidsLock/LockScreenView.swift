import SwiftUI

/// 锁屏界面：展示五年级水平汉字，需要连续答对指定题数才能解锁。
/// - 答错重置计数
/// - 家长可通过输入 PIN 码强制解锁
struct LockScreenView: View {
    @EnvironmentObject var prefs: Prefs
    @State private var bank = CharacterBank()

    // 题目状态
    @State private var currentChar: CharEntry = CharacterBank.bank[0]
    @State private var currentOptions: [String] = []
    @State private var correctAnswer = ""
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
        .persistentSystemOverlays(.hidden)
    }

    // MARK: - 认字答题

    private var quizView: some View {
        VStack(spacing: 12) {
            Text("屏幕已锁定")
                .font(.headline)
                .foregroundColor(Theme.textSecondary)
                .padding(.top, 8)

            Text(currentChar.character)
                .font(.system(size: 140, weight: .bold))
                .foregroundColor(Theme.accent)
                .minimumScaleFactor(0.5)
                .lineLimit(1)

            Text("这个字读什么？")
                .font(.title3)
                .foregroundColor(Theme.highlight)

            Text("已答对 \(correctCount)/\(requiredCount) 道题即可解锁")
                .font(.subheadline)
                .foregroundColor(Theme.textSecondary)

            // 反馈
            Text(feedbackText)
                .font(.headline)
                .foregroundColor(feedbackShown ? (wasCorrect ? Theme.correctGreen : Theme.wrongRed) : .clear)
                .frame(height: 28)

            // 4个选项 2x2
            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                ForEach(Array(currentOptions.enumerated()), id: \.offset) { idx, option in
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
                .font(.title2.weight(.medium))
                .frame(maxWidth: .infinity)
                .padding(.vertical, 16)
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
        if !answerLocked || selectedIndex == nil {
            return (Theme.bgSurface, Theme.textPrimary, Theme.primary, 1)
        }
        if index == selectedIndex {
            return wasCorrect
                ? (Theme.correctGreen, .white, Theme.correctGreen, 0)
                : (Theme.wrongRed, .white, Theme.wrongRed, 0)
        }
        if !wasCorrect && currentOptions.indices.contains(index) && currentOptions[index] == correctAnswer {
            // 答错时高亮正确答案
            return (Theme.correctGreen.opacity(0.25), Theme.correctGreen, Theme.correctGreen, 1)
        }
        return (Theme.bgSurface.opacity(0.5), Theme.textSecondary, Theme.primary.opacity(0.5), 1)
    }

    private var feedbackText: String {
        wasCorrect ? "答对了！" : "答错了，重新开始！"
    }

    private func loadNextQuestion() {
        currentChar = bank.getRandomCharacter()
        correctAnswer = currentChar.pinyin
        currentOptions = bank.getOptions(correctPinyin: correctAnswer)
        selectedIndex = nil
        answerLocked = false
        feedbackShown = false
    }

    private func onOptionSelected(_ index: Int) {
        guard !answerLocked, currentOptions.indices.contains(index) else { return }
        answerLocked = true
        selectedIndex = index
        let selected = currentOptions[index]

        if selected == correctAnswer {
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
