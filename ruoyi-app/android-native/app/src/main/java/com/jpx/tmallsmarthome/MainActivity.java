package com.jpx.tmallsmarthome;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.PermissionRequest;
import android.webkit.RenderProcessGoneDetail;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;

import java.util.ArrayList;
import java.util.List;

// T10S runs Android 10; the legacy fullscreen/navigation callbacks are kept for
// device compatibility and intentionally isolated in this native shell.
@SuppressWarnings("deprecation")
public class MainActivity extends Activity {
    public static final String ACTION_OPEN_FROM_OVERLAY =
            "com.jpx.tmallsmarthome.OPEN_FROM_OVERLAY";
    public static final String EXTRA_OPENED_FROM_OVERLAY = "opened_from_overlay";

    private static final String TAG = "TmallSmartHome";
    private static final int REQUEST_AUDIO_PERMISSION = 1001;
    private static final String START_URL = "file:///android_asset/index.html";
    private static final String PRIVACY_ACCEPTED = "privacy_accepted_v1";

    private FrameLayout webContainer;
    private WebView webView;
    private PermissionRequest pendingWebPermission;
    private boolean pageLoaded;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN,
                WindowManager.LayoutParams.FLAG_FULLSCREEN);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        enterImmersiveMode();

        webContainer = new FrameLayout(this);
        setContentView(webContainer);
        createWebView();

        if (getPreferences(MODE_PRIVATE).getBoolean(PRIVACY_ACCEPTED, false)) {
            loadStartPage();
        } else {
            showPrivacyDialog();
        }
        handleForegroundIntent(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleForegroundIntent(intent);
    }

    @Override
    protected void onResume() {
        super.onResume();
        Log.i(TAG, "onResume -> overlay foreground");
        enterImmersiveMode();
        KeepAliveService.request(this, KeepAliveService.ACTION_APP_FOREGROUND);
        resumeWebRuntime("activity_resume");
    }

    @Override
    protected void onPause() {
        // T10S 的定制系统在快速切换任务时偶尔延迟甚至跳过 onStop 回调。
        // onPause 一定发生在界面失去前台时，用它及时恢复悬浮入口；onResume 会立即隐藏。
        // 不依赖 isChangingConfigurations：T10S 桌面切换会被固件误报为配置变化。
        // 即使是真实旋转，紧随其后的 onResume 也会立即隐藏悬浮球。
        Log.i(TAG, "onPause -> overlay background");
        KeepAliveService.request(this, KeepAliveService.ACTION_APP_BACKGROUND);
        super.onPause();
    }

    @Override
    protected void onUserLeaveHint() {
        // T10S 的定制 WebView 偶尔会让 onPause 晚到数秒；用户按 Home 或切换应用时，
        // 先同步显示悬浮入口，避免桌面上短暂找不到返回入口。
        Log.i(TAG, "onUserLeaveHint -> overlay background");
        KeepAliveService.request(this, KeepAliveService.ACTION_APP_BACKGROUND);
        super.onUserLeaveHint();
    }

    @Override
    protected void onStop() {
        if (webView != null) {
            webView.onPause();
        }
        super.onStop();
    }

    private void handleForegroundIntent(Intent intent) {
        boolean fromOverlay = intent != null
                && (ACTION_OPEN_FROM_OVERLAY.equals(intent.getAction())
                || intent.getBooleanExtra(EXTRA_OPENED_FROM_OVERLAY, false));
        Log.i(TAG, "foreground intent: source=" + (fromOverlay ? "overlay" : "launcher"));
        if (webView == null && webContainer != null) {
            createWebView();
        }
        if (!pageLoaded && webView != null
                && getPreferences(MODE_PRIVATE).getBoolean(PRIVACY_ACCEPTED, false)) {
            loadStartPage();
        }
        resumeWebRuntime(fromOverlay ? "overlay" : "intent");
    }

    private void createWebView() {
        if (webContainer == null || webView != null) {
            return;
        }
        webView = new WebView(this);
        webContainer.addView(webView, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT));
        configureWebView();
    }

    private void configureWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setAllowFileAccessFromFileURLs(true);
        settings.setAllowUniversalAccessFromFileURLs(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);

        WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG);
        webView.addJavascriptInterface(new GenieJsBridge(this), "GenieBridge");
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                // Keep the privileged bridge confined to the bundled, trusted UI.
                return url == null || !url.startsWith("file:///android_asset/");
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                pageLoaded = true;
                dispatchForegroundEvent("page_finished");
            }

            @Override
            public boolean onRenderProcessGone(WebView view, RenderProcessGoneDetail detail) {
                if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
                    return false;
                }
                Log.e(TAG, "WebView renderer exited; recreating runtime. crashed="
                        + detail.didCrash());
                runOnUiThread(() -> {
                    destroyWebView();
                    createWebView();
                    loadStartPage();
                });
                return true;
            }
        });
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(PermissionRequest request) {
                runOnUiThread(() -> handleWebPermissionRequest(request));
            }

            @Override
            public void onPermissionRequestCanceled(PermissionRequest request) {
                if (pendingWebPermission == request) {
                    pendingWebPermission = null;
                }
            }
        });
    }

    private void loadStartPage() {
        if (webView == null) {
            return;
        }
        pageLoaded = false;
        webView.loadUrl(START_URL);
    }

    private void resumeWebRuntime(String source) {
        if (webView == null) {
            return;
        }
        webView.onResume();
        webView.resumeTimers();
        webView.requestFocus(View.FOCUS_DOWN);
        webView.invalidate();
        dispatchForegroundEvent(source);
    }

    private void dispatchForegroundEvent(String source) {
        if (webView == null || !pageLoaded) {
            return;
        }
        String safeSource = source == null ? "unknown"
                : source.replace("\\", "\\\\").replace("'", "\\'");
        webView.evaluateJavascript(
                "(function(){"
                        + "window.dispatchEvent(new CustomEvent('tmallAppForeground',"
                        + "{detail:{source:'" + safeSource + "'}}));"
                        + "window.dispatchEvent(new Event('focus'));"
                        + "})();",
                null);
    }

    private void handleWebPermissionRequest(PermissionRequest request) {
        List<String> allowed = new ArrayList<>();
        for (String resource : request.getResources()) {
            if (PermissionRequest.RESOURCE_AUDIO_CAPTURE.equals(resource)) {
                allowed.add(resource);
            }
        }
        if (allowed.isEmpty()) {
            request.deny();
            return;
        }
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                == PackageManager.PERMISSION_GRANTED) {
            request.grant(allowed.toArray(new String[0]));
            return;
        }
        pendingWebPermission = request;
        requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO},
                REQUEST_AUDIO_PERMISSION);
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions,
                                           int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode != REQUEST_AUDIO_PERMISSION || pendingWebPermission == null) {
            return;
        }
        PermissionRequest request = pendingWebPermission;
        pendingWebPermission = null;
        if (grantResults.length > 0
                && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            request.grant(new String[]{PermissionRequest.RESOURCE_AUDIO_CAPTURE});
        } else {
            request.deny();
        }
    }

    private void showPrivacyDialog() {
        new AlertDialog.Builder(this)
                .setTitle("天猫智家服务协议与隐私政策")
                .setMessage("欢迎使用天猫智家语音助手。实时语音功能需要使用麦克风，并通过网络将语音发送至云端完成识别与回复；当您明确要求控制低风险家居设备时，App 会把必要的设备指令提交给本机天猫精灵处理。当前版本默认不保存原始音频。继续使用即表示您同意《用户服务协议》和《隐私政策》。")
                .setCancelable(false)
                .setPositiveButton("同意并继续", (dialog, which) -> {
                    getPreferences(MODE_PRIVATE).edit()
                            .putBoolean(PRIVACY_ACCEPTED, true).apply();
                    loadStartPage();
                })
                .setNegativeButton("暂不同意", (dialog, which) -> finish())
                .show();
    }

    private void enterImmersiveMode() {
        getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                        | View.SYSTEM_UI_FLAG_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_LAYOUT_STABLE);
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) {
            enterImmersiveMode();
        }
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            moveTaskToBack(true);
        }
    }

    private void destroyWebView() {
        WebView current = webView;
        webView = null;
        pageLoaded = false;
        if (current == null) {
            return;
        }
        if (webContainer != null) {
            webContainer.removeView(current);
        }
        current.stopLoading();
        current.removeJavascriptInterface("GenieBridge");
        current.setWebChromeClient(null);
        current.setWebViewClient(null);
        current.destroy();
    }

    @Override
    protected void onDestroy() {
        destroyWebView();
        super.onDestroy();
    }
}
