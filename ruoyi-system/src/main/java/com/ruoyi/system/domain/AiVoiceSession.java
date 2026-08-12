package com.ruoyi.system.domain;

import java.util.Date;
import com.fasterxml.jackson.annotation.JsonFormat;
import com.ruoyi.common.core.domain.BaseEntity;

/**
 * 千问实时语音会话。
 */
public class AiVoiceSession extends BaseEntity
{
    private static final long serialVersionUID = 1L;

    private String sessionId;
    private String qwenSessionId;
    private String userKey;
    private Long userId;
    private String userName;
    private String nickName;
    private String clientId;
    private String clientIp;
    private String modelName;
    private String voiceName;
    private String status;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private Date startedAt;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private Date endedAt;

    private Long durationMs;
    private Integer messageCount;
    private Integer inputTextChars;
    private Integer outputTextChars;
    private String closeReason;

    public String getSessionId()
    {
        return sessionId;
    }

    public void setSessionId(String sessionId)
    {
        this.sessionId = sessionId;
    }

    public String getQwenSessionId()
    {
        return qwenSessionId;
    }

    public void setQwenSessionId(String qwenSessionId)
    {
        this.qwenSessionId = qwenSessionId;
    }

    public String getUserKey()
    {
        return userKey;
    }

    public void setUserKey(String userKey)
    {
        this.userKey = userKey;
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

    public String getClientId()
    {
        return clientId;
    }

    public void setClientId(String clientId)
    {
        this.clientId = clientId;
    }

    public String getClientIp()
    {
        return clientIp;
    }

    public void setClientIp(String clientIp)
    {
        this.clientIp = clientIp;
    }

    public String getModelName()
    {
        return modelName;
    }

    public void setModelName(String modelName)
    {
        this.modelName = modelName;
    }

    public String getVoiceName()
    {
        return voiceName;
    }

    public void setVoiceName(String voiceName)
    {
        this.voiceName = voiceName;
    }

    public String getStatus()
    {
        return status;
    }

    public void setStatus(String status)
    {
        this.status = status;
    }

    public Date getStartedAt()
    {
        return startedAt;
    }

    public void setStartedAt(Date startedAt)
    {
        this.startedAt = startedAt;
    }

    public Date getEndedAt()
    {
        return endedAt;
    }

    public void setEndedAt(Date endedAt)
    {
        this.endedAt = endedAt;
    }

    public Long getDurationMs()
    {
        return durationMs;
    }

    public void setDurationMs(Long durationMs)
    {
        this.durationMs = durationMs;
    }

    public Integer getMessageCount()
    {
        return messageCount;
    }

    public void setMessageCount(Integer messageCount)
    {
        this.messageCount = messageCount;
    }

    public Integer getInputTextChars()
    {
        return inputTextChars;
    }

    public void setInputTextChars(Integer inputTextChars)
    {
        this.inputTextChars = inputTextChars;
    }

    public Integer getOutputTextChars()
    {
        return outputTextChars;
    }

    public void setOutputTextChars(Integer outputTextChars)
    {
        this.outputTextChars = outputTextChars;
    }

    public String getCloseReason()
    {
        return closeReason;
    }

    public void setCloseReason(String closeReason)
    {
        this.closeReason = closeReason;
    }
}
