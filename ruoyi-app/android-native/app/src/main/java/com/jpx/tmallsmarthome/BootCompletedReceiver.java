package com.jpx.tmallsmarthome;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.util.Log;

/** Receives the T10S boot broadcast and schedules the app after system startup settles. */
public final class BootCompletedReceiver extends BroadcastReceiver {
    private static final String TAG = "TmallSmartHomeBoot";
    private static final String ACTION_QUICK_BOOT = "android.intent.action.QUICKBOOT_POWERON";
    private static final String ACTION_HTC_QUICK_BOOT = "com.htc.intent.action.QUICKBOOT_POWERON";

    @Override
    public void onReceive(Context context, Intent intent) {
        String action = intent == null ? null : intent.getAction();
        if (!Intent.ACTION_BOOT_COMPLETED.equals(action)
                && !Intent.ACTION_LOCKED_BOOT_COMPLETED.equals(action)
                && !ACTION_QUICK_BOOT.equals(action)
                && !ACTION_HTC_QUICK_BOOT.equals(action)) {
            return;
        }

        StartupDiagnostics.recordBootReceived(context, action);
        try {
            StartupScheduler.scheduleAfterBoot(context);
            Log.i(TAG, "boot received; app startup scheduled");
        } catch (Throwable throwable) {
            StartupDiagnostics.recordFailure(context, "schedule_failed", throwable);
            Log.e(TAG, "failed to schedule app startup", throwable);
        }
    }
}
