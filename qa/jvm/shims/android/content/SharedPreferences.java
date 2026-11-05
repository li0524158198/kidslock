package android.content;

import java.util.HashMap;
import java.util.Map;
import java.util.Set;

/** 内存版 SharedPreferences 测试替身（apply 即时生效，便于断言） */
public interface SharedPreferences {
    Map<String, Object> getAll();
    String getString(String key, String defValue);
    int getInt(String key, int defValue);
    long getLong(String key, long defValue);
    boolean getBoolean(String key, boolean defValue);

    Editor edit();

    interface Editor {
        Editor putString(String key, String value);
        Editor putInt(String key, int value);
        Editor putLong(String key, long value);
        Editor putBoolean(String key, boolean value);
        Editor remove(String key);
        Editor clear();
        boolean commit();
        void apply();
    }

    /** 可直接读写底层存储（测试时间旅行用） */
    class MemPrefs implements SharedPreferences {
        public final Map<String, Object> store = new HashMap<>();
        @Override public Map<String, Object> getAll() { return new HashMap<>(store); }
        @Override public String getString(String k, String d) { Object v = store.get(k); return v == null ? d : (String) v; }
        @Override public int getInt(String k, int d) { Object v = store.get(k); return v == null ? d : (Number) v instanceof Integer ? (Integer) v : ((Number) v).intValue(); }
        @Override public long getLong(String k, long d) { Object v = store.get(k); return v == null ? d : ((Number) v).longValue(); }
        @Override public boolean getBoolean(String k, boolean d) { Object v = store.get(k); return v == null ? d : (Boolean) v; }
        @Override public Editor edit() {
            return new Editor() {
                @Override public Editor putString(String k, String v) { store.put(k, v); return this; }
                @Override public Editor putInt(String k, int v) { store.put(k, v); return this; }
                @Override public Editor putLong(String k, long v) { store.put(k, v); return this; }
                @Override public Editor putBoolean(String k, boolean v) { store.put(k, v); return this; }
                @Override public Editor remove(String k) { store.remove(k); return this; }
                @Override public Editor clear() { store.clear(); return this; }
                @Override public boolean commit() { return true; }
                @Override public void apply() {}
            };
        }
    }
}
