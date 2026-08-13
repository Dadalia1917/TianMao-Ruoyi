package com.jpx.tmallsmarthome;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.IBinder;
import android.util.Log;

/** Foreground service owning the overlay entry while the assistant UI is in background. */
public final class KeepAliveService extends Service {
    public static final String ACTION_START = "com.jpx.tmallsmarthome.overlay.START";
    public static final String ACTION_APP_FOREGROUND =
            "com.jpx.tmallsmarthome.overlay.APP_FOREGROUND";
    public static final String ACTION_APP_BACKGROUND =
            "com.jpx.tmallsmarthome.overlay.APP_BACKGROUND";
    public static final String ACTION_STOP = "com.jpx.tmallsmarthome.overlay.STOP";

    private static final String TAG = "TmallSmartHomeKeep";
    private static final String CHANNEL_ID = "tmall_smarthome_switch";
    private static final int NOTIFICATION_ID = 1001;

    private FloatingBubble bubble;
    private boolean appInForeground;

    public static void request(Context context, String action) {
        Intent intent = new Intent(context, KeepAliveService.class).setAction(action);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            context.startForegroundService(intent);
        } else {
            context.startService(intent);
        }
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        startForeground(NOTIFICATION_ID, buildNotification());
        String action = intent == null ? ACTION_START : intent.getAction();
        if (ACTION_STOP.equals(action)) {
            hideBubble();
            stopForeground(true);
            stopSelf();
            return START_NOT_STICKY;
        }
        if (ACTION_APP_FOREGROUND.equals(action)) {
            appInForeground = true;
        } else if (ACTION_APP_BACKGROUND.equals(action) || ACTION_START.equals(action)) {
            appInForeground = false;
        }
        syncBubbleVisibility();
        return START_STICKY;
    }

    private void syncBubbleVisibility() {
        if (appInForeground) {
            hideBubble();
            return;
        }
        if (!FloatingBubble.canDrawOverlay(this)) {
            Log.w(TAG, "overlay permission unavailable");
            return;
        }
        if (bubble == null) {
            bubble = new FloatingBubble(this);
        }
        bubble.show();
    }

    private void hideBubble() {
        if (bubble != null) {
            bubble.hide();
        }
    }

    @Override
    public void onDestroy() {
        hideBubble();
        bubble = null;
        super.onDestroy();
    }

    private Notification buildNotification() {
        Context app = getApplicationContext();
        NotificationManager manager =
                (NotificationManager) app.getSystemService(Context.NOTIFICATION_SERVICE);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID, "天猫智家快捷入口", NotificationManager.IMPORTANCE_LOW);
            channel.setDescription("在天猫精灵桌面与天猫智家之间切换");
            channel.setShowBadge(false);
            manager.createNotificationChannel(channel);
        }

        Intent openApp = new Intent(app, MainActivity.class)
                .setAction(MainActivity.ACTION_OPEN_FROM_OVERLAY)
                .putExtra(MainActivity.EXTRA_OPENED_FROM_OVERLAY, true)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK
                        | Intent.FLAG_ACTIVITY_CLEAR_TOP
                        | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent pendingApp = PendingIntent.getActivity(
                app, 72, openApp, pendingIntentFlags());

        Intent openGenie = new Intent().setClassName(
                        "com.alibaba.genie.panel",
                        "com.alibaba.genie.panel.activity.SplashActivity")
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent pendingGenie = PendingIntent.getActivity(
                app, 73, openGenie, pendingIntentFlags());

        Notification.Builder builder = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? new Notification.Builder(app, CHANNEL_ID)
                : new Notification.Builder(app);
        return builder
                .setContentTitle("天猫智家语音助手")
                .setContentText("悬浮入口已就绪")
                .setSmallIcon(R.drawable.app_icon)
                .setContentIntent(pendingApp)
                .setOngoing(true)
                .setOnlyAlertOnce(true)
                .addAction(0, "打开天猫智家", pendingApp)
                .addAction(0, "回到天猫精灵", pendingGenie)
                .build();
    }

    private int pendingIntentFlags() {
        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            flags |= PendingIntent.FLAG_IMMUTABLE;
        }
        return flags;
    }
}
