package com.ruoyi.web.controller.assistant;

import java.util.List;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import com.ruoyi.common.annotation.Log;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.core.page.TableDataInfo;
import com.ruoyi.common.enums.BusinessType;
import com.ruoyi.system.domain.AiUserMemory;
import com.ruoyi.system.domain.AiVoiceSession;
import com.ruoyi.system.service.IAiAssistantService;

/**
 * 千问智能语音助手运营接口。
 */
@RestController
@RequestMapping("/assistant")
public class AiAssistantController extends BaseController
{
    @Autowired
    private IAiAssistantService assistantService;

    @PreAuthorize("@ss.hasPermi('assistant:overview:list')")
    @GetMapping("/overview")
    public AjaxResult overview()
    {
        return success(assistantService.selectOverview());
    }

    @PreAuthorize("@ss.hasPermi('assistant:session:list')")
    @GetMapping("/session/list")
    public TableDataInfo sessionList(AiVoiceSession session)
    {
        startPage();
        List<AiVoiceSession> list = assistantService.selectVoiceSessionList(session);
        return getDataTable(list);
    }

    @PreAuthorize("@ss.hasPermi('assistant:memory:list')")
    @GetMapping("/memory/list")
    public TableDataInfo memoryList(AiUserMemory memory)
    {
        startPage();
        List<AiUserMemory> list = assistantService.selectUserMemoryList(memory);
        return getDataTable(list);
    }

    @PreAuthorize("@ss.hasPermi('assistant:memory:remove')")
    @Log(title = "账号长期记忆", businessType = BusinessType.DELETE)
    @DeleteMapping("/memory/{memoryIds}")
    public AjaxResult removeMemory(@PathVariable Long[] memoryIds)
    {
        return toAjax(assistantService.deleteUserMemoryByIds(memoryIds));
    }
}
