package com.ruoyi.system.service;

import java.util.List;
import java.util.Map;
import com.ruoyi.system.domain.AiUserMemory;
import com.ruoyi.system.domain.AiVoiceSession;

/**
 * 语音助手运营服务。
 */
public interface IAiAssistantService
{
    public Map<String, Object> selectOverview();

    public List<AiVoiceSession> selectVoiceSessionList(AiVoiceSession session);

    public List<AiUserMemory> selectUserMemoryList(AiUserMemory memory);

    public int deleteUserMemoryByIds(Long[] memoryIds);
}
