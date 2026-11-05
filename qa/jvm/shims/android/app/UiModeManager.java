package android.app;

public class UiModeManager {
    public final java.util.concurrent.atomic.AtomicBoolean tv = new java.util.concurrent.atomic.AtomicBoolean();
    public UiModeManager(boolean tv) { this.tv.set(tv); }
    public int getCurrentModeType() {
        return tv.get() ? android.content.res.Configuration.UI_MODE_TYPE_TELEVISION : 0;
    }
}
