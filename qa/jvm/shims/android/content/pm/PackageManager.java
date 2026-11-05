package android.content.pm;

import android.content.ComponentName;

public class PackageManager {
    public static final int COMPONENT_ENABLED_STATE_ENABLED = 0;
    public static final int COMPONENT_ENABLED_STATE_DISABLED = 2;
    public static final int DONT_KILL_APP = 1;
    public static final String FEATURE_LEANBACK = "android.software.leanback";

    public boolean leanback = false;
    /** 记录最后一次 alias 状态，供断言 */
    public String lastAliasState = "none";

    public boolean hasSystemFeature(String feature) {
        return FEATURE_LEANBACK.equals(feature) && leanback;
    }

    public void setComponentEnabledSetting(ComponentName alias, int state, int flags) {
        lastAliasState = (alias.getShortClassName() + "→" + (state == COMPONENT_ENABLED_STATE_ENABLED ? "ENABLED" : "DISABLED"));
    }
}
