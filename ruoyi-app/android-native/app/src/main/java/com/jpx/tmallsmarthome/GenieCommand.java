package com.jpx.tmallsmarthome;

import android.content.ContentValues;
import android.content.Context;
import android.content.pm.ProviderInfo;
import android.net.Uri;

import java.util.Locale;

/**
 * Minimal, defensive wrapper around the exported Tmall Genie command provider.
 *
 * <p>ADB's {@code content insert} command is only a development-time way to verify
 * this same Android API. The installed application calls ContentResolver directly.
 */
final class GenieCommand {
    static final String AUTHORITY = "com.alibaba.ailabs.genie.assistant.provider";
    private static final Uri API_URI = Uri.parse("content://" + AUTHORITY + "/GenieApi");
    private static final int METHOD_RECOGNIZE_TEXT = 15;
    private static final int MAX_COMMAND_CHARS = 120;

    private static final String[] ACTIONS = {
            "打开", "开启", "关掉", "关闭", "调到", "调成", "设为", "设置为",
            "升高", "降低", "调高", "调低", "开", "关"
    };
    private static final String[] DEVICES = {
            "灯", "空调", "窗帘", "电视", "风扇", "空气净化器", "净化器", "普通插座"
    };
    private static final String[] REJECTED = {
            "不要", "别", "不用", "取消", "不需要", "门锁", "开锁", "燃气", "热水器",
            "车库门", "监控", "撤防", "报警器", "怎么", "如何", "为什么", "教程", "方法",
            "帮我看看", "看一下", "检查一下", "确认一下", "开了吗", "关了吗", "开着", "关着",
            "设备状态"
    };

    private GenieCommand() {
    }

    static boolean isAvailable(Context context) {
        ProviderInfo provider = context.getPackageManager().resolveContentProvider(AUTHORITY, 0);
        return provider != null && provider.exported;
    }

    static String validate(String rawCommand) {
        String command = rawCommand == null ? "" : rawCommand.trim().replaceAll("\\s+", "");
        if (command.isEmpty() || command.length() > MAX_COMMAND_CHARS) {
            throw new IllegalArgumentException("家居指令为空或过长");
        }
        for (String marker : REJECTED) {
            if (command.contains(marker)) {
                throw new IllegalArgumentException("该指令不属于可执行的低风险家居操作");
            }
        }
        if (command.contains("开关")
                && !containsAny(command, new String[]{"打开", "开启", "关闭", "关掉"})) {
            throw new IllegalArgumentException("请明确设备需要打开还是关闭");
        }
        if (!containsAny(command, ACTIONS) || !containsAny(command, DEVICES)) {
            throw new IllegalArgumentException("未识别到明确的家居设备和操作");
        }
        return command;
    }

    static void send(String command, Context context) {
        if (!isAvailable(context)) {
            throw new IllegalStateException("当前系统未提供天猫精灵指令通道");
        }
        ContentValues values = new ContentValues();
        values.put("data", command);
        values.put("method", METHOD_RECOGNIZE_TEXT);
        // StatusProvider may validly return null even after accepting the command.
        context.getContentResolver().insert(API_URI, values);
    }

    private static boolean containsAny(String text, String[] markers) {
        String normalized = text.toLowerCase(Locale.ROOT);
        for (String marker : markers) {
            if (normalized.contains(marker.toLowerCase(Locale.ROOT))) {
                return true;
            }
        }
        return false;
    }
}
