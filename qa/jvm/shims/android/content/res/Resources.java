package android.content.res;

/** 测试替身：从本地文件加载 raw 资源 */
public class Resources {
    private static String rawPath = "questions.json";
    public static void setRawPath(String p) { rawPath = p; }
    public java.io.InputStream openRawResource(int id) {
        try {
            return new java.io.FileInputStream(rawPath);
        } catch (java.io.IOException e) {
            throw new RuntimeException(e);
        }
    }
}
