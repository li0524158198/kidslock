import Foundation

// MARK: - 题目模型

struct QuestionItem: Identifiable {
    let text: String
    let bigChar: String?      // 字音题大字（其他为 nil）
    let options: [String]     // 已打乱
    let answerIndex: Int

    var id: String { text + "|" + options.joined() }
}

struct BankEntry: Identifiable {
    let id: String
    let label: String
    let isCustom: Bool
}

// MARK: - JSON 结构

private struct QuestionRaw: Codable {
    let q: String
    let opts: [String]
    let ans: Int
    let char: String?
}

private struct QuestionsRoot: Codable {
    let version: Int
    let labels: [String: String]
    let banks: [String: [QuestionRaw]]
}

private struct CustomBankEntry: Codable {
    let label: String
    let items: [QuestionRaw]
}

// MARK: - 题库引擎

/// 人教版语数英题库引擎（1-12 年级 × 3 学科 = 36 内置库）。
/// 内置题来自 questions.json；数学按年级程序生成；支持自定义题库（CSV 导入导出）。
final class QuestionBank {

    static let subjects = ["chinese", "math", "english"]
    static let subjectNames = ["语文", "数学", "英语"]
    static let gradeNames = ["一年级", "二年级", "三年级", "四年级", "五年级", "六年级",
                             "初一", "初二", "初三", "高一", "高二", "高三"]
    static let customPrefix = "custom_"

    /** 内置库显示名（subject: 0..2 学科索引，grade: 0..11 年级索引） */
    static func builtinLabel(_ subject: Int, _ grade: Int) -> String {
        return "\(subjectNames[subject])·\(gradeNames[grade])"
    }

    /** 内置库 id（subject: 0..2 学科索引，grade: 0..11 年级索引） */
    static func builtinId(_ subject: Int, _ grade: Int) -> String {
        return "\(subjects[subject])_g\(grade + 1)"
    }

    static let shared = QuestionBank()

    private var banks: [String: [QuestionRaw]] = [:]
    private var labels: [String: String] = [:]
    private var customBanks: [String: CustomBankEntry] = [:]
    private let fm = FileManager.default

    private init() {
        loadBuiltin()
        loadCustom()
    }

    private func loadBuiltin() {
        guard let url = Bundle.main.url(forResource: "questions", withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let root = try? JSONDecoder().decode(QuestionsRoot.self, from: data) else {
            return
        }
        banks = root.banks
        labels = root.labels
    }

    // MARK: 题库清单

    var bankList: [BankEntry] {
        var list: [BankEntry] = []
        for s in 0..<3 {
            for g in 1...12 {
                let id = "\(QuestionBank.subjects[s])_g\(g)"
                list.append(BankEntry(id: id, label: "\(QuestionBank.subjectNames[s])·\(QuestionBank.gradeNames[g - 1])", isCustom: false))
            }
        }
        for (id, entry) in customBanks.sorted(by: { $0.key < $1.key }) {
            list.append(BankEntry(id: id, label: entry.label, isCustom: true))
        }
        return list
    }

    func customIds() -> [String] {
        return customBanks.keys.sorted()
    }

    func customLabel(_ id: String) -> String {
        return customBanks[id]?.label ?? id
    }

    func label(_ bankId: String) -> String {
        let id = resolveBankId(bankId)
        if let e = customBanks[id] { return e.label }
        return labels[id] ?? id
    }

    /// 兼容旧版三级库 id：primary→g5、junior→g7、senior→g10
    func resolveBankId(_ bankId: String) -> String {
        if bankId.hasPrefix(QuestionBank.customPrefix) && customBanks[bankId] != nil { return bankId }
        if banks[bankId] != nil { return bankId }
        if bankId.hasSuffix("_primary") { return bankId.replacingOccurrences(of: "_primary", with: "_g5") }
        if bankId.hasSuffix("_junior") { return bankId.replacingOccurrences(of: "_junior", with: "_g7") }
        if bankId.hasSuffix("_senior") { return bankId.replacingOccurrences(of: "_senior", with: "_g10") }
        return "chinese_g1"
    }

    // MARK: 出题

    func getQuestion(_ bankId: String) -> QuestionItem {
        let id = resolveBankId(bankId)
        do {
            if id.hasPrefix(QuestionBank.customPrefix), let items = customBanks[id]?.items, !items.isEmpty {
                let raw = items.randomElement()!
                return Self.shuffle(raw.q, raw.char, raw.opts, raw.ans)
            }
            let grade = parseGrade(id)
            if id.hasPrefix("math"), grade >= 1, grade <= 9, Int.random(in: 0..<100) < 30 {
                if let gq = genMath(grade) { return gq }
            }
            guard let arr = banks[id], !arr.isEmpty else {
                throw NSError(domain: "bank", code: 1)
            }
            let raw = arr.randomElement()!
            return Self.shuffle(raw.q, raw.char, raw.opts, raw.ans)
        } catch {
            return QuestionItem(text: "出题出错，请重试", bigChar: nil,
                                options: ["1", "2", "3", "4"], answerIndex: 0)
        }
    }

    private func parseGrade(_ bankId: String) -> Int {
        guard let range = bankId.range(of: "_g") else { return -1 }
        return Int(bankId[range.upperBound...]) ?? -1
    }

    private static func shuffle(_ text: String, _ bigChar: String?, _ optsArr: [String], _ ansIdx: Int) -> QuestionItem {
        let correct = ansIdx < optsArr.count ? optsArr[ansIdx] : optsArr.first ?? ""
        var seen = Set<String>()
        var opts: [String] = []
        for o in optsArr {
            let t = o.trimmingCharacters(in: .whitespaces)
            if !t.isEmpty && seen.insert(t).inserted && opts.count < 4 {
                opts.append(t)
            }
        }
        while opts.count < 4 { opts.append("—") }
        opts.shuffle()
        let idx = opts.firstIndex(of: correct) ?? 0
        return QuestionItem(text: text, bigChar: bigChar, options: opts, answerIndex: idx)
    }

    // MARK: 数学按年级生成

    private func genMath(_ grade: Int) -> QuestionItem? {
        func ri(_ a: Int, _ b: Int) -> Int { Int.random(in: a...b) }
        func numeric(_ text: String, _ r: Int) -> QuestionItem {
            var set = Set<Int>([r])
            while set.count < 4 {
                let d = ri(1, 9) * (Int.random(in: 0..<8) == 0 ? 10 : 1)
                let v = r + (Bool.random() ? d : -d)
                if v >= 0 { set.insert(v) }
            }
            let vals = set.shuffled()
            let opts = vals.map { String($0) }
            return QuestionItem(text: text, bigChar: nil, options: opts, answerIndex: opts.firstIndex(of: String(r)) ?? 0)
        }
        switch grade {
        case 1...2:
            if Bool.random() {
                let a = ri(grade == 1 ? 1 : 11, grade == 1 ? 10 : 89)
                let b = ri(1, grade == 1 ? 10 : 89)
                return numeric("\(a) + \(b) = ?", a + b)
            }
            let a = ri(grade == 1 ? 2 : 30, grade == 1 ? 10 : 99)
            let b = ri(1, a - 1)
            return numeric("\(a) - \(b) = ?", a - b)
        case 3...4:
            let b = ri(3, 9)
            let r = ri(3, grade <= 3 ? 9 : 40)
            let a = b * r
            // 乘法标答是 a×b 本身；除法分支 a÷b = r
            return Bool.random() ? numeric("\(a) × \(b) = ?", a * b) : numeric("\(a) ÷ \(b) = ?", r)
        case 5...6:
            let a = ri(11, 60), b = ri(2, 20)
            // 五六年级未学负数：c 不超过 a+b-1，保证结果 ≥ 1
            let c = ri(5, min(40, a + b - 1))
            return numeric("\(a) + \(b) - \(c) = ?", a + b - c)
        default:
            let a = ri(2, 9), x = ri(1, 15), b = ri(1, 40)
            return numeric("解方程：\(a)x + \(b) = \(a * x + b)，x = ?", x)
        }
    }

    // MARK: CSV 导入导出

    private static let csvHead = "题干,选项A,选项B,选项C,选项D,答案,大字"

    func exportCsv(_ bankId: String) -> String {
        let id = resolveBankId(bankId)
        var items: [QuestionRaw] = []
        if id.hasPrefix(QuestionBank.customPrefix), let e = customBanks[id] {
            items = e.items
        } else if let arr = banks[id] {
            items = arr
        }
        var sb = Self.csvHead + "\r\n"
        for it in items {
            var opts: [String] = []
            for i in 0..<4 { opts.append((i < it.opts.count ? it.opts[i] : "—").replacingOccurrences(of: ",", with: "，")) }
            let ans = it.ans < 4 ? ["A", "B", "C", "D"][it.ans] : "A"
            let big = it.char ?? ""
            let cells = ([it.q] + opts + [ans, big]).map { cell($0) }
            sb += cells.joined(separator: ",") + "\r\n"
        }
        return sb
    }

    private func cell(_ s: String) -> String {
        if s.contains(",") || s.contains("\"") || s.contains("\n") {
            return "\"" + s.replacingOccurrences(of: "\"", with: "\"\"") + "\""
        }
        return s
    }

    /// 从 CSV 文本导入为自定义库（覆盖同名）。
    /// 返回实际保存的自定义库 id（文件名已净化，调用方必须用该 id 选中题库）。格式错误抛异常。
    func importCsv(name: String, csvText: String) throws -> String {
        var items: [QuestionRaw] = []
        let clean = csvText.replacingOccurrences(of: "\u{FEFF}", with: "").replacingOccurrences(of: "\r\n", with: "\n")
        var lines = clean.components(separatedBy: "\n")
        if let first = lines.first, first.contains("题干") { lines.removeFirst() }
        for line in lines {
            let c = parseCsvLine(line)
            guard c.count >= 6 else { continue }
            let q = c[0].trimmingCharacters(in: .whitespaces)
            guard !q.isEmpty else { continue }
            var ans = 0
            if let idx = ["A", "B", "C", "D"].firstIndex(of: c[5].trimmingCharacters(in: .whitespaces).uppercased()) {
                ans = idx
            }
            let big = c.count > 6 ? c[6].trimmingCharacters(in: .whitespaces) : ""
            items.append(QuestionRaw(q: q,
                                     opts: [c[1], c[2], c[3], c[4]].map { $0.trimmingCharacters(in: .whitespaces) },
                                     ans: ans,
                                     char: big.isEmpty ? nil : big))
        }
        guard !items.isEmpty else {
            throw NSError(domain: "csv", code: 2, userInfo: [NSLocalizedDescriptionKey: "没有解析到有效题目"])
        }
        let safe = name.replacingOccurrences(of: "[\\\\/:*?\"<>|]", with: "_", options: .regularExpression)
        let id = QuestionBank.customPrefix + safe
        customBanks[id] = CustomBankEntry(label: "自定义·\(safe)", items: items)
        saveCustom()
        return id
    }

    /// 某题库的题目数（内置库或自定义库）
    func bankSize(_ bankId: String) -> Int {
        let id = resolveBankId(bankId)
        if id.hasPrefix(QuestionBank.customPrefix) {
            return customBanks[id]?.items.count ?? 0
        }
        return banks[id]?.count ?? 0
    }

    /// 极简 CSV 行解析（支持双引号）
    private func parseCsvLine(_ line: String) -> [String] {
        var cells: [String] = []
        var cur = ""
        var inQuote = false
        var it = line.startIndex
        while it < line.endIndex {
            let ch = line[it]
            if inQuote {
                if ch == "\"" {
                    let next = line.index(after: it)
                    if next < line.endIndex && line[next] == "\"" {
                        cur.append("\"")
                        it = next
                    } else {
                        inQuote = false
                    }
                } else {
                    cur.append(ch)
                }
            } else if ch == "\"" {
                inQuote = true
            } else if ch == "," {
                cells.append(cur); cur = ""
            } else {
                cur.append(ch)
            }
            it = line.index(after: it)
        }
        cells.append(cur)
        return cells
    }

    // MARK: 自定义库持久化

    private var customFileURL: URL {
        fm.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("custom_banks.json")
    }

    private func saveCustom() {
        if let data = try? JSONEncoder().encode(customBanks) {
            try? data.write(to: customFileURL)
        }
    }

    private func loadCustom() {
        if let data = try? Data(contentsOf: customFileURL),
           let decoded = try? JSONDecoder().decode([String: CustomBankEntry].self, from: data) {
            customBanks = decoded
        }
    }
}
