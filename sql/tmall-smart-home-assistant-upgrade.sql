-- 天猫智家·千问智能语音助手数据库升级脚本
-- 适用数据库：MySQL 8 / ry-cat
-- 执行前请备份生产数据库。本脚本会永久删除若依代码生成与 Quartz 调度表。

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
START TRANSACTION;

-- 1. 移除本项目不使用的后台示例菜单与权限关系。
DELETE FROM `sys_role_menu`
WHERE `menu_id` IN (3, 4, 110, 115, 116, 117,
                    1049, 1050, 1051, 1052, 1053, 1054,
                    1055, 1056, 1057, 1058, 1059, 1060);

DELETE FROM `sys_menu`
WHERE `menu_id` IN (3, 4, 110, 115, 116, 117,
                    1049, 1050, 1051, 1052, 1053, 1054,
                    1055, 1056, 1057, 1058, 1059, 1060);

-- 2. 新增语音助手运营菜单。固定 ID 便于测试与后续升级。
INSERT INTO `sys_menu`
(`menu_id`, `menu_name`, `parent_id`, `order_num`, `path`, `component`, `route_name`, `query`,
 `is_frame`, `is_cache`, `menu_type`, `visible`, `status`, `perms`, `icon`,
 `create_by`, `create_time`, `update_by`, `update_time`, `remark`)
VALUES
(5, '语音助手运营', 0, 1, 'assistant', NULL, '', '', 1, 0, 'M', '0', '0',
 'assistant:overview:list', 'dashboard', 'admin', NOW(), '', NULL, '千问智能语音助手运营目录'),
(118, '语音会话', 5, 1, 'session', 'assistant/session/index', '', '', 1, 0, 'C', '0', '0',
 'assistant:session:list', 'phone', 'admin', NOW(), '', NULL, '实时语音会话运营数据'),
(119, '长期记忆', 5, 2, 'memory', 'assistant/memory/index', '', '', 1, 0, 'C', '0', '0',
 'assistant:memory:list', 'documentation', 'admin', NOW(), '', NULL, '账号长期记忆管理'),
(1061, '删除长期记忆', 119, 1, '#', '', '', '', 1, 0, 'F', '0', '0',
 'assistant:memory:remove', '#', 'admin', NOW(), '', NULL, '')
ON DUPLICATE KEY UPDATE
 `menu_name` = VALUES(`menu_name`), `parent_id` = VALUES(`parent_id`), `order_num` = VALUES(`order_num`),
 `path` = VALUES(`path`), `component` = VALUES(`component`), `menu_type` = VALUES(`menu_type`),
 `visible` = VALUES(`visible`), `status` = VALUES(`status`), `perms` = VALUES(`perms`),
 `icon` = VALUES(`icon`), `remark` = VALUES(`remark`), `update_time` = NOW();

-- 普通运营角色默认可查看语音会话、长期记忆，并可删除错误记忆。
INSERT IGNORE INTO `sys_role_menu` (`role_id`, `menu_id`)
VALUES (2, 5), (2, 118), (2, 119), (2, 1061);

UPDATE `sys_menu` SET `menu_name` = '平台配置', `order_num` = 2, `remark` = '账号、权限及基础配置' WHERE `menu_id` = 1;
UPDATE `sys_menu` SET `menu_name` = '运行监控', `order_num` = 3, `remark` = '后台服务与审计监控' WHERE `menu_id` = 2;

-- 3. 删除调度功能专属字典。
DELETE FROM `sys_dict_data` WHERE `dict_type` IN ('sys_job_status', 'sys_job_group');
DELETE FROM `sys_dict_type` WHERE `dict_type` IN ('sys_job_status', 'sys_job_group');

-- 4. 将演示组织结构压缩为本项目实际使用的三层数据。
UPDATE `sys_user` SET `dept_id` = 101 WHERE `user_id` = 1;
UPDATE `sys_user` SET `dept_id` = 102 WHERE `user_id` = 2;
DELETE FROM `sys_role_dept` WHERE `dept_id` BETWEEN 103 AND 109;
DELETE FROM `sys_dept` WHERE `dept_id` BETWEEN 103 AND 109;

UPDATE `sys_dept`
SET `parent_id` = 0, `ancestors` = '0', `dept_name` = '无锡捷普迅智能科技有限公司',
    `order_num` = 0, `leader` = '', `phone` = '', `email` = ''
WHERE `dept_id` = 100;
UPDATE `sys_dept`
SET `parent_id` = 100, `ancestors` = '0,100', `dept_name` = '语音助手运营中心',
    `order_num` = 1, `leader` = '', `phone` = '', `email` = ''
WHERE `dept_id` = 101;
UPDATE `sys_dept`
SET `parent_id` = 100, `ancestors` = '0,100', `dept_name` = '消费者服务中心',
    `order_num` = 2, `leader` = '', `phone` = '', `email` = ''
WHERE `dept_id` = 102;

-- 5. 将样例岗位和用户资料改为运营平台语义。
DELETE FROM `sys_user_post`;
DELETE FROM `sys_post`;
INSERT INTO `sys_post`
(`post_id`, `post_code`, `post_name`, `post_sort`, `status`, `create_by`, `create_time`, `update_by`, `update_time`, `remark`)
VALUES
(1, 'platform_admin', '平台管理员', 1, '0', 'admin', NOW(), '', NULL, '管理运营后台与权限'),
(2, 'voice_operator', '语音运营', 2, '0', 'admin', NOW(), '', NULL, '查看语音会话与长期记忆'),
(3, 'customer_service', '消费者服务', 3, '0', 'admin', NOW(), '', NULL, '处理消费者账号与反馈');
INSERT INTO `sys_user_post` (`user_id`, `post_id`) VALUES (1, 1), (2, 2);

UPDATE `sys_user`
SET `nick_name` = '平台管理员', `email` = '', `phonenumber` = '', `remark` = '天猫智家运营后台管理员'
WHERE `user_id` = 1;
UPDATE `sys_user`
SET `user_name` = 'operator', `nick_name` = '语音运营员', `email` = '', `phonenumber` = '', `remark` = '语音助手运营测试账号'
WHERE `user_id` = 2;

-- 6. 替换若依演示公告与配置说明。
DELETE FROM `sys_notice` WHERE `notice_id` IN (1, 2, 3);
INSERT INTO `sys_notice`
(`notice_id`, `notice_title`, `notice_type`, `notice_content`, `status`, `create_by`, `create_time`, `update_by`, `update_time`, `remark`)
VALUES
(1, '天猫智家·千问智能语音助手运营平台已启用', '2',
 '<p>运营平台用于查看实时语音会话、跨会话长期记忆和服务运行情况。系统默认不保存用户原始音频。</p>',
 '0', 'admin', NOW(), '', NULL, '平台初始化公告')
ON DUPLICATE KEY UPDATE `notice_title` = VALUES(`notice_title`), `notice_content` = VALUES(`notice_content`), `update_time` = NOW();

UPDATE `sys_config` SET `config_name` = '运营后台-账号初始密码', `config_value` = '123456', `remark` = '新建运营账号的初始密码' WHERE `config_key` = 'sys.user.initPassword';
UPDATE `sys_config` SET `config_name` = '消费者账号-验证码开关', `remark` = '登录和注册是否启用验证码' WHERE `config_key` = 'sys.account.captchaEnabled';
UPDATE `sys_config` SET `config_name` = '消费者账号-注册开关', `config_value` = 'true', `remark` = '是否允许消费者自行注册账号' WHERE `config_key` = 'sys.account.registerUser';

COMMIT;

-- 7. 删除未被本项目引用的若依代码生成与 Quartz 调度表。
DROP TABLE IF EXISTS `gen_table_column`;
DROP TABLE IF EXISTS `gen_table`;
DROP TABLE IF EXISTS `sys_job_log`;
DROP TABLE IF EXISTS `sys_job`;
DROP TABLE IF EXISTS `qrtz_blob_triggers`;
DROP TABLE IF EXISTS `qrtz_calendars`;
DROP TABLE IF EXISTS `qrtz_cron_triggers`;
DROP TABLE IF EXISTS `qrtz_fired_triggers`;
DROP TABLE IF EXISTS `qrtz_job_details`;
DROP TABLE IF EXISTS `qrtz_locks`;
DROP TABLE IF EXISTS `qrtz_paused_trigger_grps`;
DROP TABLE IF EXISTS `qrtz_scheduler_state`;
DROP TABLE IF EXISTS `qrtz_simple_triggers`;
DROP TABLE IF EXISTS `qrtz_simprop_triggers`;
DROP TABLE IF EXISTS `qrtz_triggers`;

SET FOREIGN_KEY_CHECKS = 1;
