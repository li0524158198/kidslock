import Foundation

/// 五年级水平汉字题库。
/// 每道题：展示一个汉字，从4个拼音选项中选出正确读音。
struct CharEntry: Identifiable, Equatable {
    let character: String
    let pinyin: String
    var id: String { character }
}

struct CharacterBank {

    static let bank: [CharEntry] = [
        CharEntry(character: "誉", pinyin: "yù"),
        CharEntry(character: "邦", pinyin: "bāng"),
        CharEntry(character: "餐", pinyin: "cān"),
        CharEntry(character: "沧", pinyin: "cāng"),
        CharEntry(character: "巢", pinyin: "cháo"),
        CharEntry(character: "撑", pinyin: "chēng"),
        CharEntry(character: "炽", pinyin: "chì"),
        CharEntry(character: "储", pinyin: "chǔ"),
        CharEntry(character: "簇", pinyin: "cù"),
        CharEntry(character: "岱", pinyin: "dài"),
        CharEntry(character: "涤", pinyin: "dí"),
        CharEntry(character: "淀", pinyin: "diàn"),
        CharEntry(character: "鼎", pinyin: "dǐng"),
        CharEntry(character: "锻", pinyin: "duàn"),
        CharEntry(character: "恩", pinyin: "ēn"),
        CharEntry(character: "伐", pinyin: "fá"),
        CharEntry(character: "仿", pinyin: "fǎng"),
        CharEntry(character: "绯", pinyin: "fēi"),
        CharEntry(character: "蜂", pinyin: "fēng"),
        CharEntry(character: "赋", pinyin: "fù"),
        CharEntry(character: "钢", pinyin: "gāng"),
        CharEntry(character: "隔", pinyin: "gé"),
        CharEntry(character: "弧", pinyin: "hú"),
        CharEntry(character: "焕", pinyin: "huàn"),
        CharEntry(character: "惶", pinyin: "huáng"),
        CharEntry(character: "慧", pinyin: "huì"),
        CharEntry(character: "寂", pinyin: "jì"),
        CharEntry(character: "驾", pinyin: "jià"),
        CharEntry(character: "歼", pinyin: "jiān"),
        CharEntry(character: "茧", pinyin: "jiǎn"),
        CharEntry(character: "俭", pinyin: "jiǎn"),
        CharEntry(character: "嚼", pinyin: "jué"),
        CharEntry(character: "襟", pinyin: "jīn"),
        CharEntry(character: "钧", pinyin: "jūn"),
        CharEntry(character: "咖", pinyin: "kā"),
        CharEntry(character: "恳", pinyin: "kěn"),
        CharEntry(character: "叩", pinyin: "kòu"),
        CharEntry(character: "窟", pinyin: "kū"),
        CharEntry(character: "框", pinyin: "kuàng"),
        CharEntry(character: "溃", pinyin: "kuì"),
        CharEntry(character: "辣", pinyin: "là"),
        CharEntry(character: "揽", pinyin: "lǎn"),
        CharEntry(character: "烙", pinyin: "lào"),
        CharEntry(character: "蕾", pinyin: "lěi"),
        CharEntry(character: "凛", pinyin: "lǐn"),
        CharEntry(character: "拎", pinyin: "līn"),
        CharEntry(character: "隆", pinyin: "lóng"),
        CharEntry(character: "搂", pinyin: "lǒu"),
        CharEntry(character: "鹿", pinyin: "lù"),
        CharEntry(character: "履", pinyin: "lǚ"),
        CharEntry(character: "峦", pinyin: "luán"),
        CharEntry(character: "掠", pinyin: "lüè"),
        CharEntry(character: "脉", pinyin: "mài"),
        CharEntry(character: "盲", pinyin: "máng"),
        CharEntry(character: "贸", pinyin: "mào"),
        CharEntry(character: "朦", pinyin: "méng"),
        CharEntry(character: "弥", pinyin: "mí"),
        CharEntry(character: "觅", pinyin: "mì"),
        CharEntry(character: "蔑", pinyin: "miè"),
        CharEntry(character: "铭", pinyin: "míng"),
        CharEntry(character: "陌", pinyin: "mò"),
        CharEntry(character: "钮", pinyin: "niǔ"),
        CharEntry(character: "诺", pinyin: "nuò"),
        CharEntry(character: "畔", pinyin: "pàn"),
        CharEntry(character: "抛", pinyin: "pāo"),
        CharEntry(character: "喷", pinyin: "pēn"),
        CharEntry(character: "鹏", pinyin: "péng"),
        CharEntry(character: "聘", pinyin: "pìn"),
        CharEntry(character: "魄", pinyin: "pò"),
        CharEntry(character: "剖", pinyin: "pōu"),
        CharEntry(character: "祈", pinyin: "qí"),
        CharEntry(character: "契", pinyin: "qì"),
        CharEntry(character: "歉", pinyin: "qiàn"),
        CharEntry(character: "腔", pinyin: "qiāng"),
        CharEntry(character: "俏", pinyin: "qiào"),
        CharEntry(character: "窃", pinyin: "qiè"),
        CharEntry(character: "钦", pinyin: "qīn"),
        CharEntry(character: "躯", pinyin: "qū"),
        CharEntry(character: "趋", pinyin: "qū"),
        CharEntry(character: "雀", pinyin: "què"),
        CharEntry(character: "嚷", pinyin: "rǎng"),
        CharEntry(character: "绕", pinyin: "rào"),
        CharEntry(character: "刃", pinyin: "rèn"),
        CharEntry(character: "戎", pinyin: "róng"),
        CharEntry(character: "锐", pinyin: "ruì"),
        CharEntry(character: "辱", pinyin: "rǔ"),
        CharEntry(character: "嫂", pinyin: "sǎo"),
        CharEntry(character: "莎", pinyin: "shā"),
        CharEntry(character: "韶", pinyin: "sháo"),
        CharEntry(character: "誓", pinyin: "shì"),
        CharEntry(character: "舒", pinyin: "shū"),
        CharEntry(character: "鼠", pinyin: "shǔ"),
        CharEntry(character: "栓", pinyin: "shuān"),
        CharEntry(character: "硕", pinyin: "shuò"),
        CharEntry(character: "撕", pinyin: "sī"),
        CharEntry(character: "肆", pinyin: "sì"),
        CharEntry(character: "颂", pinyin: "sòng"),
        CharEntry(character: "俗", pinyin: "sú"),
        CharEntry(character: "遂", pinyin: "suì"),
        CharEntry(character: "贪", pinyin: "tān"),
        CharEntry(character: "毯", pinyin: "tǎn"),
        CharEntry(character: "滔", pinyin: "tāo"),
        CharEntry(character: "藤", pinyin: "téng"),
        CharEntry(character: "恬", pinyin: "tián"),
        CharEntry(character: "廷", pinyin: "tíng"),
        CharEntry(character: "凸", pinyin: "tū"),
        CharEntry(character: "颓", pinyin: "tuí"),
        CharEntry(character: "褪", pinyin: "tuì"),
        CharEntry(character: "婉", pinyin: "wǎn"),
        CharEntry(character: "亡", pinyin: "wáng"),
        CharEntry(character: "枉", pinyin: "wǎng"),
        CharEntry(character: "巍", pinyin: "wēi"),
        CharEntry(character: "蔚", pinyin: "wèi"),
        CharEntry(character: "涡", pinyin: "wō"),
        CharEntry(character: "污", pinyin: "wū"),
        CharEntry(character: "熄", pinyin: "xī"),
        CharEntry(character: "狭", pinyin: "xiá"),
        CharEntry(character: "弦", pinyin: "xián"),
        CharEntry(character: "馅", pinyin: "xiàn"),
        CharEntry(character: "翔", pinyin: "xiáng"),
        CharEntry(character: "卸", pinyin: "xiè"),
        CharEntry(character: "械", pinyin: "xiè"),
        CharEntry(character: "辛", pinyin: "xīn"),
        CharEntry(character: "锈", pinyin: "xiù"),
        CharEntry(character: "崖", pinyin: "yá"),
        CharEntry(character: "宴", pinyin: "yàn"),
        CharEntry(character: "秧", pinyin: "yāng"),
        CharEntry(character: "妖", pinyin: "yāo"),
        CharEntry(character: "钥", pinyin: "yuè"),
        CharEntry(character: "蕴", pinyin: "yùn"),
        CharEntry(character: "咋", pinyin: "zǎ"),
        CharEntry(character: "榨", pinyin: "zhà"),
        CharEntry(character: "瞻", pinyin: "zhān"),
        CharEntry(character: "障", pinyin: "zhàng"),
        CharEntry(character: "哲", pinyin: "zhé"),
        CharEntry(character: "轴", pinyin: "zhóu"),
        CharEntry(character: "铸", pinyin: "zhù"),
        CharEntry(character: "拽", pinyin: "zhuài"),
        CharEntry(character: "篆", pinyin: "zhuàn"),
        CharEntry(character: "桩", pinyin: "zhuāng"),
        CharEntry(character: "浊", pinyin: "zhuó"),
        CharEntry(character: "滋", pinyin: "zī"),
        CharEntry(character: "棕", pinyin: "zōng"),
        CharEntry(character: "奏", pinyin: "zòu"),
    ]

    private var recentIndices: [Int] = []
    private static let recentMemory = 10

    /// 随机取一道题（尽量不与最近用过的重复）。
    mutating func getRandomCharacter() -> CharEntry {
        var idx = 0
        var attempts = 0
        repeat {
            idx = Int.random(in: 0..<Self.bank.count)
            attempts += 1
        } while recentIndices.contains(idx) && attempts < 20
        recentIndices.append(idx)
        if recentIndices.count > Self.recentMemory {
            recentIndices.removeFirst()
        }
        return Self.bank[idx]
    }

    /// 生成一道完整题目：正确答案 + 3个干扰项，打乱顺序。
    mutating func getOptions(correctPinyin: String) -> [String] {
        var used: Set<String> = [correctPinyin]
        var result: [String] = []
        var attempts = 0
        while result.count < 3 && attempts < 100 {
            let py = Self.bank.randomElement()!.pinyin
            if !used.contains(py) {
                used.insert(py)
                result.append(py)
            }
            attempts += 1
        }
        result.append(correctPinyin)
        return result.shuffled()
    }
}
