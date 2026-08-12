package com.jpx.tmallsmarthome;

import android.content.Context;
import android.content.SharedPreferences;
import android.os.SystemClock;
import android.os.Build;

/** Small local audit trail for diagnosing future firmware/boot-policy changes through ADB. */
public final class StartupDiagnostics {
    private static final String PREFERENCES = "startup_diagnostics";

    private StartupDiagnostics() {
    }

    public static void recordBootReceived(Context context, String action) {
        SharedPreferences preferences = preferences(context);
        preferences.edit()
                .putInt("boot_receive_count", preferences.getInt("boot_receive_count", 0) + 1)
                .putString("last_stage", "boot_received")
                .putString("last_action", action == null ? "" : action)
                .putLong("last_wall_time_ms", System.currentTimeMillis())
                .putLong("last_elapsed_ms", SystemClock.elapsedRealtime())
                .remove("last_error")
                .apply();
    }

    public static void recordAlarmScheduled(
            Context context,
            long triggerAt,
            long delayMillis,
            int attempt,
            int totalAttempts
    ) {
        preferences(context).edit()
                .putString("last_stage", "boot_alarm_scheduled")
                .putLong("alarm_trigger_elapsed_ms", triggerAt)
                .putLong("alarm_delay_ms", delayMillis)
                .putInt("scheduled_attempt", attempt)
                .putInt("scheduled_attempts_total", totalAttempts)
                .putLong("last_wall_time_ms", System.currentTimeMillis())
                .remove("last_error")
                .apply();
    }

    public static void recordAppStarted(Context context) {
        preferences(context).edit()
                .putString("last_stage", "app_started_after_boot")
                .putLong("last_wall_time_ms", System.currentTimeMillis())
                .putLong("last_elapsed_ms", SystemClock.elapsedRealtime())
                .remove("last_error")
                .apply();
    }

    public static void recordFailure(Context context, String stage, Throwable throwable) {
        String message = throwable.getClass().getSimpleName();
        if (throwable.getMessage() != null && !throwable.getMessage().isEmpty()) {
            message += ": " + throwable.getMessage();
        }
        preferences(context).edit()
                .putString("last_stage", stage)
                .putString("last_error", message)
                .putLong("last_wall_time_ms", System.currentTimeMillis())
                .apply();
    }

    private static SharedPreferences preferences(Context context) {
        Context storageContext = context;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            storageContext = context.createDeviceProtectedStorageContext();
        }
        return storageContext.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE);
    }
}
