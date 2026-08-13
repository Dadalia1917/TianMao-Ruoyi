package com.jpx.tmallsmarthome;

import android.content.Context;
import android.webkit.JavascriptInterface;

import org.json.JSONException;
import org.json.JSONObject;

/** JavaScript surface exposed only to the bundled assistant UI. */
public final class GenieJsBridge {
    private final Context appContext;

    GenieJsBridge(Context context) {
        this.appContext = context.getApplicationContext();
    }

    @JavascriptInterface
    public boolean isAvailable() {
        // 能力协商只表示原生桥已安装。provider 的最终可用性由真实 insert
        // 决定，不能用 resolveContentProvider() 的可见性结果提前否决。
        return GenieCommand.isAvailable(appContext);
    }

    @JavascriptInterface
    public String sendToGenie(String rawCommand) {
        try {
            String command = GenieCommand.validate(rawCommand);
            GenieCommand.send(command, appContext);
            return result(true, "指令已提交给天猫精灵");
        } catch (SecurityException error) {
            return result(false, "系统拒绝访问天猫精灵指令通道");
        } catch (IllegalArgumentException | IllegalStateException error) {
            return result(false, error.getMessage());
        } catch (RuntimeException error) {
            return result(false, "天猫精灵指令通道暂不可用");
        }
    }

    private static String result(boolean accepted, String message) {
        JSONObject payload = new JSONObject();
        try {
            payload.put("accepted", accepted);
            payload.put("message", message == null ? "" : message);
        } catch (JSONException ignored) {
            return accepted
                    ? "{\"accepted\":true,\"message\":\"\"}"
                    : "{\"accepted\":false,\"message\":\"\"}";
        }
        return payload.toString();
    }
}
