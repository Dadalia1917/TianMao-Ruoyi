package com.jpx.tmallsmarthome;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.SystemClock;

/**
 * Uses system-owned Activity PendingIntents. T10S services become ready in several phases, so
 * multiple idempotent attempts are scheduled instead of relying on a single timing window.
 */
public final class StartupScheduler {
    public static final String ACTION_OPEN_AFTER_BOOT =
            "com.jpx.tmallsmarthome.OPEN_AFTER_BOOT";

    private static final int REQUEST_CODE_BASE = 1001;
    private static final long[] BOOT_DELAYS_MS = {8_000L, 25_000L, 60_000L};

    private StartupScheduler() {
    }

    public static void scheduleAfterBoot(Context context) {
        Context appContext = context.getApplicationContext();
        AlarmManager alarmManager = appContext.getSystemService(AlarmManager.class);
        if (alarmManager == null) {
            throw new IllegalStateException("AlarmManager unavailable");
        }

        long baseElapsed = SystemClock.elapsedRealtime();
        for (int index = 0; index < BOOT_DELAYS_MS.length; index++) {
            long delayMillis = BOOT_DELAYS_MS[index];
            long triggerAt = baseElapsed + delayMillis;
            PendingIntent pendingIntent = createLaunchPendingIntent(appContext, index);
            try {
                alarmManager.setExactAndAllowWhileIdle(
                        AlarmManager.ELAPSED_REALTIME_WAKEUP,
                        triggerAt,
                        pendingIntent
                );
            } catch (SecurityException exactAlarmDenied) {
                alarmManager.setAndAllowWhileIdle(
                        AlarmManager.ELAPSED_REALTIME_WAKEUP,
                        triggerAt,
                        pendingIntent
                );
            }
            StartupDiagnostics.recordAlarmScheduled(
                    appContext,
                    triggerAt,
                    delayMillis,
                    index + 1,
                    BOOT_DELAYS_MS.length
            );
        }
    }

    private static PendingIntent createLaunchPendingIntent(Context context, int attemptIndex) {
        Intent launchIntent = new Intent(context, MainActivity.class)
                .setAction(ACTION_OPEN_AFTER_BOOT + "." + attemptIndex)
                .putExtra(MainActivity.EXTRA_STARTED_AFTER_BOOT, true)
                .putExtra(MainActivity.EXTRA_BOOT_ATTEMPT, attemptIndex + 1)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK
                        | Intent.FLAG_ACTIVITY_CLEAR_TOP
                        | Intent.FLAG_ACTIVITY_SINGLE_TOP
                        | Intent.FLAG_ACTIVITY_REORDER_TO_FRONT);

        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            flags |= PendingIntent.FLAG_IMMUTABLE;
        }
        return PendingIntent.getActivity(
                context,
                REQUEST_CODE_BASE + attemptIndex,
                launchIntent,
                flags
        );
    }
}
