package com.ruoyi.system.mapper;

import java.util.List;
import java.util.Map;
import com.ruoyi.system.domain.AiUserMemory;
import com.ruoyi.system.domain.AiVoiceSession;

/**
 * 语音助手运营数据访问层。
 */
public interface AiAssistantMapper
{
    public Map<String, Object> selectOverview();

    public List<AiVoiceSession> selectVoiceSessionList(AiVoiceSession session);

    public List<AiUserMemory> selectUserMemoryList(AiUserMemory memory);

    public int deleteUserMemoryByIds(Long[] memoryIds);
}
