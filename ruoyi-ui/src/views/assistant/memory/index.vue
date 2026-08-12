<template>
  <div class="app-container assistant-page">
    <div class="page-heading">
      <div>
        <h2>账号长期记忆</h2>
        <p>记忆按登录账号隔离，会在新的语音会话中自动注入。</p>
      </div>
      <el-tag effect="light">仅保留结构化文字记忆</el-tag>
    </div>

    <el-card shadow="never" class="filter-card">
      <el-form ref="queryRef" :model="queryParams" :inline="true" label-width="72px">
        <el-form-item label="账号" prop="userName">
          <el-input v-model="queryParams.userName" placeholder="账号或昵称" clearable @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="分类" prop="category">
          <el-select v-model="queryParams.category" placeholder="全部分类" clearable>
            <el-option label="个人信息" value="profile" /><el-option label="偏好" value="preference" />
            <el-option label="关系" value="relationship" /><el-option label="计划" value="plan" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="queryParams.status" placeholder="全部状态" clearable>
            <el-option label="有效" value="0" /><el-option label="已删除" value="1" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" icon="Search" @click="handleQuery">查询</el-button>
          <el-button icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <div class="table-actions">
        <el-button type="danger" plain icon="Delete" :disabled="!selectedIds.length" @click="handleDelete"
          v-hasPermi="['assistant:memory:remove']">删除所选记忆</el-button>
        <span>删除采用逻辑删除，可保留审计痕迹。</span>
      </div>
      <el-table v-loading="loading" :data="memoryList" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="48" />
        <el-table-column label="账号" min-width="140">
          <template #default="scope"><strong>{{ scope.row.nickName || scope.row.userName || `用户 ${scope.row.userId}` }}</strong><br><small class="muted">{{ scope.row.userName }}</small></template>
        </el-table-column>
        <el-table-column label="分类" prop="category" width="110"><template #default="scope"><el-tag effect="plain">{{ categoryLabel(scope.row.category) }}</el-tag></template></el-table-column>
        <el-table-column label="记忆内容" prop="memoryValue" min-width="360" show-overflow-tooltip />
        <el-table-column label="置信度" prop="confidence" width="100" align="center"><template #default="scope">{{ Math.round(Number(scope.row.confidence || 0) * 100) }}%</template></el-table-column>
        <el-table-column label="状态" prop="status" width="90" align="center"><template #default="scope"><el-tag :type="scope.row.status === '0' ? 'success' : 'info'">{{ scope.row.status === '0' ? '有效' : '已删除' }}</el-tag></template></el-table-column>
        <el-table-column label="最近使用" prop="lastUsedAt" width="180" />
        <el-table-column label="更新时间" prop="updateTime" width="180" />
        <el-table-column label="操作" width="90" align="center">
          <template #default="scope"><el-button v-if="scope.row.status === '0'" link type="danger" @click="handleDelete(scope.row.memoryId)" v-hasPermi="['assistant:memory:remove']">删除</el-button></template>
        </el-table-column>
      </el-table>
      <pagination v-show="total > 0" :total="total" v-model:page="queryParams.pageNum"
        v-model:limit="queryParams.pageSize" @pagination="getList" />
    </el-card>
  </div>
</template>

<script setup name="AssistantMemory">
import { deleteUserMemory, listUserMemories } from '@/api/assistant'

const { proxy } = getCurrentInstance()
const loading = ref(false)
const memoryList = ref([])
const selectedIds = ref([])
const total = ref(0)
const queryParams = ref({ pageNum: 1, pageSize: 10, userName: undefined, category: undefined, status: '0' })
const categoryNames = { profile: '个人信息', preference: '偏好', relationship: '关系', plan: '计划', other: '其他' }
function categoryLabel(value) { return categoryNames[value] || value || '其他' }
function getList() {
  loading.value = true
  listUserMemories(queryParams.value).then(response => {
    memoryList.value = response.rows || []
    total.value = response.total || 0
  }).finally(() => { loading.value = false })
}
function handleQuery() { queryParams.value.pageNum = 1; getList() }
function resetQuery() { proxy.resetForm('queryRef'); queryParams.value.status = '0'; handleQuery() }
function handleSelectionChange(rows) { selectedIds.value = rows.map(item => item.memoryId) }
function handleDelete(id) {
  const ids = id || selectedIds.value
  proxy.$modal.confirm('确认删除所选长期记忆吗？后续新会话将不再使用这些内容。').then(() => deleteUserMemory(ids)).then(() => {
    proxy.$modal.msgSuccess('记忆已删除')
    getList()
  }).catch(() => {})
}
getList()
</script>

<style scoped lang="scss">
.assistant-page { background: #f6f8fc; min-height: calc(100vh - 84px); }
.page-heading { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px;
  h2 { margin: 0 0 6px; color: #17213a; } p { margin: 0; color: #7b8499; } }
.filter-card, .table-card { border: 1px solid #e9edf5; border-radius: 14px; }
.filter-card { margin-bottom: 16px; :deep(.el-form-item) { margin-bottom: 0; } :deep(.el-input), :deep(.el-select) { width: 220px; } }
.table-actions { display: flex; align-items: center; gap: 14px; margin-bottom: 14px; color: #9aa2b4; font-size: 13px; }
.muted { color: #9aa2b4; }
</style>
