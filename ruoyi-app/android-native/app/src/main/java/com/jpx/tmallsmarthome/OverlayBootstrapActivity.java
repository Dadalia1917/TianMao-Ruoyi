package com.jpx.tmallsmarthome;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.util.Log;
import android.view.Gravity;
import android.view.Window;
import android.view.WindowManager;

/**
 * Invisible T10S boot bridge. The vendor firmware drops a foreground-service start issued
 * directly by a boot receiver, while the same request from an Activity is accepted.
 */
public final class OverlayBootstrapActivity extends Activity {
    public static final String ACTION_BOOTSTRAP_OVERLAY =
            "com.jpx.tmallsmarthome.overlay.BOOTSTRAP";
    private static final String TAG = "TmallSmartHomeBoot";
    private boolean serviceRequested;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Window window = getWindow();
        WindowManager.LayoutParams params = window.getAttributes();
        params.width = 1;
        params.height = 1;
        params.gravity = Gravity.TOP | Gravity.START;
        params.dimAmount = 0f;
        window.setAttributes(params);
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (serviceRequested) {
            return;
        }
        serviceRequested = true;
        // Wait until ActivityManager has promoted this transparent bridge to RESUMED.
        new Handler(getMainLooper()).postDelayed(this::startOverlayAndFinish, 120L);
    }

    private void startOverlayAndFinish() {
        try {
            KeepAliveService.request(this, KeepAliveService.ACTION_START);
            Log.i(TAG, "overlay service requested from invisible bootstrap activity");
        } catch (RuntimeException error) {
            Log.e(TAG, "failed to request overlay service from bootstrap activity", error);
        } finally {
            new Handler(getMainLooper()).postDelayed(() -> {
                finish();
                overridePendingTransition(0, 0);
            }, 180L);
        }
    }
}
