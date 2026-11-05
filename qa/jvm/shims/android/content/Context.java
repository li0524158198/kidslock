package android.content;

/** Context 测试替身：覆盖被测源码用到的方法 */
public class Context {
    public static final int MODE_PRIVATE = 0;
    public static final String UI_MODE_SERVICE = "uimode";

    private final SharedPreferences prefs = new SharedPreferences.MemPrefs();
    public boolean tvDevice = false; // 测试可切换

    public Context getApplicationContext() { return this; }
    public SharedPreferences getSharedPreferences(String name, int mode) { return prefs; }
    public android.content.res.Resources getResources() { return new android.content.res.Resources(); }
    public java.io.File getFilesDir() {
        // 沙箱目录：run 脚本通过 -Dkidslock.filedir 固定到 qa/jvm/filedir（不入库），
        // 未指定时退回相对路径 "filedir"（保持旧行为）
        java.io.File f = new java.io.File(System.getProperty("kidslock.filedir", "filedir"));
        f.mkdirs();
        return f;
    }
    public java.io.FileOutputStream openFileOutput(String name, int mode) throws java.io.IOException {
        return new java.io.FileOutputStream(new java.io.File(getFilesDir(), name));
    }
    private final android.app.UiModeManager umm = new android.app.UiModeManager(false);
    private final android.content.pm.PackageManager pm = new android.content.pm.PackageManager();
    public Object getSystemService(String name) { umm.tv.set(tvDevice); return umm; }
    public android.content.pm.PackageManager getPackageManager() { return pm; }
}
