import SwiftUI

/// 主题色，与 Android 版 colors.xml 保持一致。
enum Theme {
    static let bgDark = Color(hex: 0x0D1B2A)
    static let bgSurface = Color(hex: 0x1B263B)
    static let bgSurfaceLight = Color(hex: 0x243447)
    static let primary = Color(hex: 0x415A77)
    static let accent = Color(hex: 0xE0E1DD)
    static let highlight = Color(hex: 0x778DA9)

    static let textPrimary = Color(hex: 0xE0E1DD)
    static let textSecondary = Color(hex: 0x778DA9)

    static let correctGreen = Color(hex: 0x2A9D5C)
    static let wrongRed = Color(hex: 0xE63946)
    static let warningOrange = Color(hex: 0xF4A261)
}

extension Color {
    init(hex: UInt32) {
        self.init(
            .sRGB,
            red: Double((hex >> 16) & 0xFF) / 255,
            green: Double((hex >> 8) & 0xFF) / 255,
            blue: Double(hex & 0xFF) / 255,
            opacity: 1
        )
    }
}


// MARK: - CSV 导出文档

import UniformTypeIdentifiers

struct CsvDocument: FileDocument {
    static var readableContentTypes: [UTType] { [.commaSeparatedText] }
    var text: String

    init(text: String) {
        self.text = text
    }

    init(configuration: ReadConfiguration) throws {
        if let data = configuration.file.regularFileContents,
           let s = String(data: data, encoding: .utf8) {
            text = s
        } else {
            text = ""
        }
    }

    func fileWrapper(configuration: WriteConfiguration) throws -> FileWrapper {
        FileWrapper(regularFileWithContents: text.data(using: .utf8) ?? Data())
    }
}
