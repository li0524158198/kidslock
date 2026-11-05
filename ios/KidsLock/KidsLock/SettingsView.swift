import SwiftUI

/// 设置主界面。
/// 家长可以在这里配置：自动继续、观看时长、解锁题数、家长PIN码。
/// 还可以开始/停止计时、立即锁屏、查看剩余时间。
struct SettingsView: View {
    @EnvironmentObject var prefs: Prefs
    @State private var now = Date()
    @State private var currentSubject = 0
    @State private var refreshTick = 0
    @State private var showImporter = false
    @State private var showExporter = false
    @State private var showImportError = false
    @State private var importErrorText = ""
    private var qb: QuestionBank { QuestionBank.shared }

    private let timer = Timer.publish(every: 1, on: .main, in: .common).autoconnect()

    private var appVersion: String {
        "v" + (Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0")
    }

    /// 从已保存题库解析年级索引（0..11），自定义库或解析失败回退 0（一年级）
    private func savedGrade() -> Int {
        let id = qb.resolveBankId(prefs.bankId)
        guard let range = id.range(of: "_g"), let g = Int(id[range.upperBound...]), (1...12).contains(g) else {
            return 0
        }
        return g - 1
    }

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 16) {
                    Text(appVersion)
                        .font(.caption)
                        .foregroundColor(Theme.textSecondary)
                    statusCard
                    bankCard
                    configCard
                    controlCard
                }
                .padding(16)
            }
            .background(Theme.bgDark.ignoresSafeArea())
            .navigationTitle("儿童锁屏")
            .navigationBarTitleDisplayMode(.inline)
        }
        .navigationViewStyle(.stack)
        .onAppear {
            // 从已保存题库反推学科，保持按钮高亮与实际一致
            let id = qb.resolveBankId(prefs.bankId)
            if let idx = QuestionBank.subjects.firstIndex(where: { id.hasPrefix($0) }) {
                currentSubject = idx
            }
        }
        .onReceive(timer) { _ in
            now = Date()
            checkExpiry()
        }
        .alert("设置家长PIN码（4位数字）", isPresented: $pinDialogShown) {
            TextField("4位数字", text: $pinInput)
                .keyboardType(.numberPad)
            Button("确定") {
                if pinInput.count == 4 && pinInput.allSatisfy(\.isNumber) {
                    prefs.setParentPin(pinInput)
                }
            }
            Button("取消", role: .cancel) {}
        } message: {
            Text(prefs.isPinDefault ? "当前PIN：默认 1234（建议修改）" : "当前PIN：已设置")
        }
    }

    // MARK: - 状态卡片

    private var statusCard: some View {
        VStack(spacing: 10) {
            if prefs.isLocked {
                statusText("当前状态：已锁屏", color: Theme.wrongRed)
                Text("请答题解锁")
                    .font(.title3)
                    .foregroundColor(Theme.textSecondary)
            } else if prefs.timerActive {
                let remaining = prefs.remainingMillis
                if remaining <= 0 {
                    statusText("当前状态：时间到", color: Theme.wrongRed)
                } else {
                    statusText("当前状态：计时中", color: Theme.correctGreen)
                    Text("剩余时间：\(formatTime(remaining))")
                        .font(.system(.title2, design: .monospaced))
                        .foregroundColor(Theme.accent)
                }
            } else {
                statusText("当前状态：未计时", color: Theme.textSecondary)
            }
        }
        .frame(maxWidth: .infinity)
        .padding()
        .background(RoundedRectangle(cornerRadius: 12).fill(Theme.bgSurface))
    }

    private func statusText(_ s: String, color: Color) -> some View {
        Text(s).font(.headline).foregroundColor(color)
    }

    // MARK: - 题库选择卡片（人教版 学科×年级 + 自定义 CSV）

    private var bankCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            sectionTitle("答题题库（人教版）")

            HStack(spacing: 8) {
                ForEach(0..<3, id: \.self) { si in
                    Button(QuestionBank.subjectNames[si]) {
                        // 切学科 = 保留当前年级、立即切换题库
                        currentSubject = si
                        prefs.bankId = QuestionBank.builtinId(si, savedGrade())
                        refreshTick += 1
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 10)
                    .background(RoundedRectangle(cornerRadius: 8)
                        .fill(currentSubject == si ? Theme.highlight : Theme.bgSurfaceLight))
                    .foregroundColor(currentSubject == si ? Theme.bgDark : Theme.textPrimary)
                }
            }

            LazyVGrid(columns: Array(repeating: GridItem(.flexible()), count: 6), spacing: 8) {
                ForEach(0..<12, id: \.self) { gi in
                    let id = QuestionBank.builtinId(currentSubject, gi)
                    let selected = prefs.bankId == id
                    Button(QuestionBank.gradeNames[gi]) {
                        prefs.bankId = id
                        refreshTick += 1
                    }
                    .font(.subheadline)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 10)
                    .background(RoundedRectangle(cornerRadius: 8)
                        .fill(selected ? Theme.highlight : Theme.bgSurfaceLight)
                        .overlay(RoundedRectangle(cornerRadius: 8)
                            .strokeBorder(selected ? Theme.correctGreen : .clear, lineWidth: 2)))
                    .foregroundColor(selected ? Theme.bgDark : Theme.textPrimary)
                }
            }

            if !qb.customIds().isEmpty {
                Text("我的自定义题库").font(.subheadline).foregroundColor(Theme.textSecondary)
                ForEach(qb.customIds(), id: \.self) { cid in
                    let selected = prefs.bankId == cid
                    Button(qb.customLabel(cid)) {
                        prefs.bankId = cid
                        refreshTick += 1
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 10)
                    .background(RoundedRectangle(cornerRadius: 8)
                        .fill(Theme.bgSurfaceLight)
                        .overlay(RoundedRectangle(cornerRadius: 8)
                            .strokeBorder(selected ? Theme.correctGreen : .clear, lineWidth: 2)))
                    .foregroundColor(selected ? Theme.correctGreen : Theme.textPrimary)
                }
            }

            HStack(spacing: 8) {
                Button("导入 CSV 题库") { showImporter = true }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 10)
                    .background(RoundedRectangle(cornerRadius: 8).fill(Theme.primary))
                    .foregroundColor(Theme.accent)
                Button("导出当前题库 CSV") { showExporter = true }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 10)
                    .background(RoundedRectangle(cornerRadius: 8).fill(Theme.primary))
                    .foregroundColor(Theme.accent)
            }
        }
        .padding()
        .background(RoundedRectangle(cornerRadius: 12).fill(Theme.bgSurface))
        .id(refreshTick)
        .fileImporter(isPresented: $showImporter, allowedContentTypes: [.commaSeparatedText]) { result in
            if case .success(let url) = result {
                let secured = url.startAccessingSecurityScopedResource()
                defer { if secured { url.stopAccessingSecurityScopedResource() } }
                do {
                    let text = try String(contentsOf: url, encoding: .utf8)
                    var name = url.lastPathComponent
                    if name.lowercased().hasSuffix(".csv") { name.removeLast(4) }
                    prefs.bankId = try qb.importCsv(name: name, csvText: text)
                    refreshTick += 1
                } catch {
                    importErrorText = error.localizedDescription.isEmpty ? "文件格式无法识别" : error.localizedDescription
                    showImportError = true
                }
            }
        }
        .alert("导入失败", isPresented: $showImportError) {
            Button("好", role: .cancel) {}
        } message: {
            Text(importErrorText)
        }
        .fileExporter(isPresented: $showExporter,
                      document: CsvDocument(text: qb.exportCsv(prefs.bankId)),
                      contentType: .commaSeparatedText,
                      defaultFilename: prefs.bankId + ".csv") { result in
            // 导出完成（成功与否系统已提示）
        }
    }

    // MARK: - 参数配置卡片

    private var configCard: some View {
        VStack(alignment: .leading, spacing: 14) {
            sectionTitle("参数配置")

            Toggle(isOn: $prefs.autoStart) {
                Text(prefs.autoStart ? "自动继续：已开启" : "自动继续：已关闭")
                    .foregroundColor(Theme.textPrimary)
            }
            .tint(Theme.highlight)

            Divider().overlay(Theme.highlight)

            VStack(alignment: .leading, spacing: 8) {
                Text("观看时长：\(prefs.formatDuration(prefs.watchLimitSeconds))")
                    .foregroundColor(Theme.textPrimary)
                timePicker
            }

            Divider().overlay(Theme.highlight)

            VStack(alignment: .leading, spacing: 8) {
                Text("解锁题数：\(prefs.unlockCount) 道连续答对")
                    .foregroundColor(Theme.textPrimary)
                countPicker
            }

            Divider().overlay(Theme.highlight)

            Button {
                showPinDialog()
            } label: {
                Text("设置家长PIN")
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 12)
                    .background(RoundedRectangle(cornerRadius: 8).fill(Theme.primary))
                    .foregroundColor(Theme.accent)
            }
        }
        .padding()
        .background(RoundedRectangle(cornerRadius: 12).fill(Theme.bgSurface))
    }

    private var timePicker: some View {
        HStack(spacing: 8) {
            ForEach([30, 900, 1800, 2700, 3600, 5400, 7200], id: \.self) { sec in
                Button(sec < 60 ? "\(sec)秒" : "\(sec / 60)分") {
                    prefs.watchLimitSeconds = sec
                }
                .padding(.vertical, 8)
                .frame(maxWidth: .infinity)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(prefs.watchLimitSeconds == sec ? Theme.highlight : Theme.bgSurfaceLight)
                )
                .foregroundColor(prefs.watchLimitSeconds == sec ? Theme.bgDark : Theme.textPrimary)
            }
        }
    }

    private var countPicker: some View {
        HStack(spacing: 8) {
            ForEach([3, 5, 10], id: \.self) { count in
                Button(count.description) {
                    prefs.unlockCount = count
                }
                .padding(.vertical, 8)
                .frame(maxWidth: .infinity)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(prefs.unlockCount == count ? Theme.highlight : Theme.bgSurfaceLight)
                )
                .foregroundColor(prefs.unlockCount == count ? Theme.bgDark : Theme.textPrimary)
            }
        }
    }

    // MARK: - 计时控制卡片

    private var controlCard: some View {
        VStack(alignment: .leading, spacing: 14) {
            sectionTitle("计时控制")

            Button {
                prefs.startTimer(seconds: prefs.watchLimitSeconds)
            } label: {
                Text(prefs.timerActive ? "重新开始计时" : "开始计时")
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .background(RoundedRectangle(cornerRadius: 8).fill(Theme.correctGreen))
                    .foregroundColor(.white)
                    .font(.headline)
            }

            Button {
                prefs.stopTimer()
            } label: {
                Text("停止计时")
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .background(RoundedRectangle(cornerRadius: 8).fill(Theme.primary))
                    .foregroundColor(Theme.accent)
            }

            Button {
                prefs.stopTimer()
                prefs.isLocked = true
            } label: {
                Text("立即锁屏")
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .background(RoundedRectangle(cornerRadius: 8).fill(Theme.wrongRed))
                    .foregroundColor(.white)
            }
        }
        .padding()
        .background(RoundedRectangle(cornerRadius: 12).fill(Theme.bgSurface))
    }

    private func sectionTitle(_ s: String) -> some View {
        Text(s).font(.headline).foregroundColor(Theme.highlight)
    }

    // MARK: - 到时自动锁屏

    private func checkExpiry() {
        if !prefs.isLocked && prefs.isTimerExpired {
            prefs.timerActive = false
            prefs.isLocked = true
        }
    }

    // MARK: - 设置 PIN 弹窗

    @State private var pinDialogShown = false
    @State private var pinInput = ""

    private func showPinDialog() {
        pinInput = ""
        pinDialogShown = true
    }

    // MARK: - Formatting

    private func formatTime(_ millis: Double) -> String {
        let total = Int(millis / 1000)
        return String(format: "%02d:%02d", total / 60, total % 60)
    }
}
