import request from '@/utils/request'

export function getAssistantOverview() {
  return request({
    url: '/assistant/overview',
    method: 'get'
  })
}

export function listVoiceSessions(query) {
  return request({
    url: '/assistant/session/list',
    method: 'get',
    params: query
  })
}

export function listUserMemories(query) {
  return request({
    url: '/assistant/memory/list',
    method: 'get',
    params: query
  })
}

export function deleteUserMemory(memoryIds) {
  return request({
    url: `/assistant/memory/${memoryIds}`,
    method: 'delete'
  })
}
