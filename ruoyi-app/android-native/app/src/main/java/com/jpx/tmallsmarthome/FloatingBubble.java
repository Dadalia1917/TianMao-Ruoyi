package com.jpx.tmallsmarthome;

import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.PixelFormat;
import android.graphics.Point;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.SystemClock;
import android.provider.Settings;
import android.util.Log;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewConfiguration;
import android.view.WindowManager;
import android.widget.ImageView;

/** Draggable, debounced entry bubble shown only while the assistant is in background. */
public final class FloatingBubble {
    private static final String TAG = "TmallSmartHomeBubble";
    private static final String PREFS = "floating_bubble";
    private static final String PREF_X = "x";
    private static final String PREF_Y = "y";
    private static final long CLICK_DEBOUNCE_MS = 800L;

    private final Context context;
    private final SharedPreferences preferences;
    private WindowManager windowManager;
    private View bubbleView;
    private WindowManager.LayoutParams layoutParams;
    private long lastOpenElapsed;

    public FloatingBubble(Context context) {
        this.context = context.getApplicationContext();
        this.preferences = this.context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    public static boolean canDrawOverlay(Context context) {
        return Build.VERSION.SDK_INT < Build.VERSION_CODES.M
                || Settings.canDrawOverlays(context);
    }

    public void show() {
        if (bubbleView != null || !canDrawOverlay(context)) {
            return;
        }
        windowManager = (WindowManager) context.getSystemService(Context.WINDOW_SERVICE);
        if (windowManager == null) {
            return;
        }

        float density = context.getResources().getDisplayMetrics().density;
        int size = Math.round(64 * density);
        int edge = Math.round(20 * density);

        ImageView bubble = new ImageView(context);
        bubble.setImageResource(R.drawable.floating_bubble_icon);
        bubble.setScaleType(ImageView.ScaleType.CENTER_INSIDE);
        int padding = Math.round(4 * density);
        bubble.setPadding(padding, padding, padding, padding);
        bubble.setContentDescription("打开天猫智家");
        bubble.setElevation(12 * density);

        GradientDrawable background = new GradientDrawable();
        background.setShape(GradientDrawable.OVAL);
        background.setColor(0xFFFFFCF8);
        background.setStroke(Math.max(1, Math.round(density)), 0x66DCA67D);
        bubble.setBackground(background);
        bubble.setOnClickListener(view -> openApplication());

        layoutParams = new WindowManager.LayoutParams(
                size,
                size,
                Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                        ? WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
                        : WindowManager.LayoutParams.TYPE_PHONE,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                        | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL
                        | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
                PixelFormat.TRANSLUCENT);
        layoutParams.gravity = Gravity.TOP | Gravity.START;

        Point screen = screenSize();
        layoutParams.x = preferences.getInt(PREF_X, Math.max(edge, screen.x - size - edge));
        layoutParams.y = preferences.getInt(PREF_Y, Math.round(120 * density));
        clampToScreen(screen, size);
        bubble.setOnTouchListener(new DragTouchListener(size));

        try {
            windowManager.addView(bubble, layoutParams);
            bubbleView = bubble;
        } catch (RuntimeException error) {
            Log.e(TAG, "failed to add overlay", error);
            layoutParams = null;
        }
    }

    public void hide() {
        View current = bubbleView;
        bubbleView = null;
        if (current == null || windowManager == null) {
            return;
        }
        try {
            windowManager.removeView(current);
        } catch (RuntimeException ignored) {
            // The window may already have been reclaimed by the firmware.
        }
    }

    private void openApplication() {
        long now = SystemClock.elapsedRealtime();
        if (now - lastOpenElapsed < CLICK_DEBOUNCE_MS) {
            return;
        }
        lastOpenElapsed = now;
        Intent intent = new Intent(context, MainActivity.class)
                .setAction(MainActivity.ACTION_OPEN_FROM_OVERLAY)
                .putExtra(MainActivity.EXTRA_OPENED_FROM_OVERLAY, true)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK
                        | Intent.FLAG_ACTIVITY_CLEAR_TOP
                        | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            flags |= PendingIntent.FLAG_IMMUTABLE;
        }
        try {
            PendingIntent.getActivity(context, 71, intent, flags).send();
        } catch (PendingIntent.CanceledException error) {
            Log.e(TAG, "failed to open assistant", error);
        }
    }

    private Point screenSize() {
        Point screen = new Point();
        windowManager.getDefaultDisplay().getRealSize(screen);
        return screen;
    }

    private void clampToScreen(Point screen, int size) {
        layoutParams.x = Math.max(0, Math.min(layoutParams.x, Math.max(0, screen.x - size)));
        layoutParams.y = Math.max(0, Math.min(layoutParams.y, Math.max(0, screen.y - size)));
    }

    private final class DragTouchListener implements View.OnTouchListener {
        private final int size;
        private final int touchSlop = ViewConfiguration.get(context).getScaledTouchSlop();
        private float downRawX;
        private float downRawY;
        private int startX;
        private int startY;
        private boolean dragging;

        DragTouchListener(int size) {
            this.size = size;
        }

        @Override
        public boolean onTouch(View view, MotionEvent event) {
            if (layoutParams == null || windowManager == null) {
                return false;
            }
            switch (event.getActionMasked()) {
                case MotionEvent.ACTION_DOWN:
                    downRawX = event.getRawX();
                    downRawY = event.getRawY();
                    startX = layoutParams.x;
                    startY = layoutParams.y;
                    dragging = false;
                    return true;
                case MotionEvent.ACTION_MOVE:
                    float deltaX = event.getRawX() - downRawX;
                    float deltaY = event.getRawY() - downRawY;
                    if (!dragging && Math.hypot(deltaX, deltaY) >= touchSlop) {
                        dragging = true;
                    }
                    if (dragging) {
                        layoutParams.x = startX + Math.round(deltaX);
                        layoutParams.y = startY + Math.round(deltaY);
                        clampToScreen(screenSize(), size);
                        try {
                            windowManager.updateViewLayout(view, layoutParams);
                        } catch (RuntimeException error) {
                            Log.w(TAG, "failed to move overlay", error);
                        }
                    }
                    return true;
                case MotionEvent.ACTION_UP:
                    if (dragging) {
                        preferences.edit()
                                .putInt(PREF_X, layoutParams.x)
                                .putInt(PREF_Y, layoutParams.y)
                                .apply();
                    } else {
                        view.performClick();
                    }
                    return true;
                case MotionEvent.ACTION_CANCEL:
                    return true;
                default:
                    return false;
            }
        }
    }
}
