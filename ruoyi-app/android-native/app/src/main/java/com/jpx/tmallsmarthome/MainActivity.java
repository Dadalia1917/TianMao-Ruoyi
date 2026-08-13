package com.jpx.tmallsmarthome;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.pm.PackageManager;
import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import java.util.ArrayList;
import java.util.List;

// T10S runs Android 10; the legacy fullscreen/navigation callbacks are kept for
// device compatibility and intentionally isolated in this native shell.
@SuppressWarnings("deprecation")
public class MainActivity extends Activity {
    public static final String EXTRA_STARTED_AFTER_BOOT = "started_after_boot";
    public static final String EXTRA_BOOT_ATTEMPT = "boot_attempt";
    private static final int REQUEST_AUDIO_PERMISSION = 1001;
    private static final String START_URL = "file:///android_asset/index.html";
    private static final String PREFS = "tmall_smart_home_prefs";
    private static final String PRIVACY_ACCEPTED = "privacy_accepted_v1";

    private WebView webView;
    private PermissionRequest pendingWebPermission;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        recordBootLaunch(getIntent());
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN,
                WindowManager.LayoutParams.FLAG_FULLSCREEN);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        enterImmersiveMode();

        webView = new WebView(this);
        setContentView(webView);
        configureWebView();

        if (getPreferences(MODE_PRIVATE).getBoolean(PRIVACY_ACCEPTED, false)) {
            webView.loadUrl(START_URL);
        } else {
            showPrivacyDialog();
        }
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        recordBootLaunch(intent);
    }

    private void recordBootLaunch(Intent intent) {
        if (intent != null && intent.getBooleanExtra(EXTRA_STARTED_AFTER_BOOT, false)) {
            StartupDiagnostics.recordAppStarted(this);
        }
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
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
            request.grant(allowed.toArray(new String[0]));
            return;
        }
        pendingWebPermission = request;
        requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, REQUEST_AUDIO_PERMISSION);
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode != REQUEST_AUDIO_PERMISSION || pendingWebPermission == null) {
            return;
        }
        PermissionRequest request = pendingWebPermission;
        pendingWebPermission = null;
        if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
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
                    getPreferences(MODE_PRIVATE).edit().putBoolean(PRIVACY_ACCEPTED, true).apply();
                    webView.loadUrl(START_URL);
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
            super.onBackPressed();
        }
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.stopLoading();
            webView.removeJavascriptInterface("GenieBridge");
            webView.setWebChromeClient(null);
            webView.setWebViewClient(null);
            webView.destroy();
            webView = null;
        }
        super.onDestroy();
    }
}
