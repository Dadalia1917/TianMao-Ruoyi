package com.ruoyi.system.service.impl;

import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import com.ruoyi.system.domain.AiUserMemory;
import com.ruoyi.system.domain.AiVoiceSession;
import com.ruoyi.system.mapper.AiAssistantMapper;
import com.ruoyi.system.service.IAiAssistantService;

/**
 * 语音助手运营服务实现。
 */
@Service
public class AiAssistantServiceImpl implements IAiAssistantService
{
    @Autowired
    private AiAssistantMapper assistantMapper;

    @Override
    public Map<String, Object> selectOverview()
    {
        return assistantMapper.selectOverview();
    }

    @Override
    public List<AiVoiceSession> selectVoiceSessionList(AiVoiceSession session)
    {
        return assistantMapper.selectVoiceSessionList(session);
    }

    @Override
    public List<AiUserMemory> selectUserMemoryList(AiUserMemory memory)
    {
        return assistantMapper.selectUserMemoryList(memory);
    }

    @Override
    public int deleteUserMemoryByIds(Long[] memoryIds)
    {
        return assistantMapper.deleteUserMemoryByIds(memoryIds);
    }
}
