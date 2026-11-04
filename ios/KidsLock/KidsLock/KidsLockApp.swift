import SwiftUI

@main
struct KidsLockApp: App {
    @StateObject private var prefs = Prefs.shared

    init() {
        // 启动时恢复状态：锁屏状态 / 计时超时检查（对应 Android 的开机自启逻辑）
        Prefs.shared.restoreOnLaunch()
    }

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(prefs)
                .preferredColorScheme(.dark)
        }
    }
}

/// 根视图：锁屏状态下强制显示锁屏界面（防止从桌面图标绕过锁屏）。
struct RootView: View {
    @EnvironmentObject var prefs: Prefs

    var body: some View {
        ZStack {
            Theme.bgDark.ignoresSafeArea()
            if prefs.isLocked {
                LockScreenView()
                    .transition(.opacity)
            } else {
                SettingsView()
                    .transition(.opacity)
            }
        }
        .animation(.easeInOut(duration: 0.25), value: prefs.isLocked)
    }
}
