package com.jpx.tmallsmarthome;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.util.Log;

/** Starts only the small overlay service after boot; it never opens MainActivity. */
public final class OverlayBootReceiver extends BroadcastReceiver {
    private static final String TAG = "TmallSmartHomeBoot";

    @Override
    public void onReceive(Context context, Intent intent) {
        String action = intent == null ? null : intent.getAction();
        if (!Intent.ACTION_BOOT_COMPLETED.equals(action)
                && !Intent.ACTION_LOCKED_BOOT_COMPLETED.equals(action)
                && !"android.intent.action.QUICKBOOT_POWERON".equals(action)
                && !"com.htc.intent.action.QUICKBOOT_POWERON".equals(action)) {
            return;
        }
        try {
            KeepAliveService.request(context, KeepAliveService.ACTION_START);
            Log.i(TAG, "overlay service started after boot; assistant UI remains closed");
        } catch (RuntimeException error) {
            Log.e(TAG, "failed to start overlay service after boot", error);
        }
    }
}
