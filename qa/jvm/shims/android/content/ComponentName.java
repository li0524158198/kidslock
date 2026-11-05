package android.content;

public class ComponentName {
    private final String pkg, cls;
    public ComponentName(Object context, String cls) {
        this.pkg = "com.kidslock.app";
        this.cls = cls;
    }
    public String getShortClassName() { return cls; }
}
