package com.ruoyi.system.domain;

import java.math.BigDecimal;
import java.util.Date;
import com.fasterxml.jackson.annotation.JsonFormat;
import com.ruoyi.common.core.domain.BaseEntity;

/**
 * 语音助手账号长期记忆。
 */
public class AiUserMemory extends BaseEntity
{
    private static final long serialVersionUID = 1L;

    private Long memoryId;
    private Long userId;
    private String userName;
    private String nickName;
    private String memoryKey;
    private String category;
    private String memoryValue;
    private BigDecimal confidence;
    private String sourceSessionId;
    private String status;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private Date lastUsedAt;

    public Long getMemoryId()
    {
        return memoryId;
    }

    public void setMemoryId(Long memoryId)
    {
        this.memoryId = memoryId;
    }

    public Long getUserId()
    {
        return userId;
    }

    public void setUserId(Long userId)
    {
        this.userId = userId;
    }

    public String getUserName()
    {
        return userName;
    }

    public void setUserName(String userName)
    {
        this.userName = userName;
    }

    public String getNickName()
    {
        return nickName;
    }

    public void setNickName(String nickName)
    {
        this.nickName = nickName;
    }

    public String getMemoryKey()
    {
        return memoryKey;
    }

    public void setMemoryKey(String memoryKey)
    {
        this.memoryKey = memoryKey;
    }

    public String getCategory()
    {
        return category;
    }

    public void setCategory(String category)
    {
        this.category = category;
    }

    public String getMemoryValue()
    {
        return memoryValue;
    }

    public void setMemoryValue(String memoryValue)
    {
        this.memoryValue = memoryValue;
    }

    public BigDecimal getConfidence()
    {
        return confidence;
    }

    public void setConfidence(BigDecimal confidence)
    {
        this.confidence = confidence;
    }

    public String getSourceSessionId()
    {
        return sourceSessionId;
    }

    public void setSourceSessionId(String sourceSessionId)
    {
        this.sourceSessionId = sourceSessionId;
    }

    public String getStatus()
    {
        return status;
    }

    public void setStatus(String status)
    {
        this.status = status;
    }

    public Date getLastUsedAt()
    {
        return lastUsedAt;
    }

    public void setLastUsedAt(Date lastUsedAt)
    {
        this.lastUsedAt = lastUsedAt;
    }
}
