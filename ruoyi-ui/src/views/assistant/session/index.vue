<template>
  <div class="app-container assistant-page">
    <div class="page-heading">
      <div>
        <h2>语音会话</h2>
        <p>查看消费者与 Qwen3.5 Omni 的实时语音会话状态和质量数据。</p>
      </div>
      <el-tag type="success" effect="light">不保存原始音频</el-tag>
    </div>

    <el-card shadow="never" class="filter-card">
      <div class="filter-card-head">
        <div class="filter-heading-copy">
          <span>筛选会话</span>
          <small>按账号、连接状态、模型和时间范围定位记录</small>
        </div>
        <div class="filter-actions">
          <el-button type="primary" icon="Search" @click="handleQuery">查询</el-button>
          <el-button icon="Refresh" @click="resetQuery">重置</el-button>
        </div>
      </div>
      <el-form ref="queryRef" :model="queryParams" label-position="top" class="filter-form">
        <div class="filter-grid">
          <el-form-item label="账号" prop="userName">
            <el-input v-model="queryParams.userName" placeholder="账号、昵称或隔离键" clearable @keyup.enter="handleQuery" />
          </el-form-item>
          <el-form-item label="状态" prop="status">
            <el-select v-model="queryParams.status" placeholder="全部状态" clearable>
              <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="模型" prop="modelName">
            <el-input v-model="queryParams.modelName" placeholder="例如 qwen3.5-omni" clearable @keyup.enter="handleQuery" />
          </el-form-item>
          <el-form-item label="开始时间" class="date-item">
            <el-date-picker v-model="dateRange" value-format="YYYY-MM-DD HH:mm:ss" type="daterange"
              range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" />
          </el-form-item>
        </div>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <el-table v-loading="loading" :data="sessionList">
        <el-table-column label="账号" min-width="150">
          <template #default="scope">
            <div class="account-cell">
              <span>{{ scope.row.nickName || scope.row.userName || '匿名设备' }}</span>
              <small>{{ scope.row.userName || scope.row.userKey }}</small>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" prop="status" width="110" align="center">
          <template #default="scope"><el-tag :type="statusType(scope.row.status)" effect="light">{{ statusLabel(scope.row.status) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="模型 / 音色" min-width="210">
          <template #default="scope"><span>{{ scope.row.modelName }}</span><br><small class="muted">{{ scope.row.voiceName }}</small></template>
        </el-table-column>
        <el-table-column label="会话时长" width="120" align="center">
          <template #default="scope">{{ formatDuration(scope.row.durationMs) }}</template>
        </el-table-column>
        <el-table-column label="消息数" prop="messageCount" width="90" align="center" />
        <el-table-column label="客户端 IP" prop="clientIp" min-width="140" show-overflow-tooltip />
        <el-table-column label="开始时间" prop="startedAt" width="180" />
        <el-table-column label="结束原因" prop="closeReason" min-width="180" show-overflow-tooltip />
      </el-table>
      <pagination v-show="total > 0" :total="total" v-model:page="queryParams.pageNum"
        v-model:limit="queryParams.pageSize" @pagination="getList" />
    </el-card>
  </div>
</template>

<script setup name="VoiceSession">
import { listVoiceSessions } from '@/api/assistant'

const { proxy } = getCurrentInstance()
const loading = ref(false)
const sessionList = ref([])
const total = ref(0)
const dateRange = ref([])
const queryParams = ref({ pageNum: 1, pageSize: 10, userName: undefined, status: undefined, modelName: undefined })
const statusOptions = [
  { label: '连接中', value: 'connecting' }, { label: '对话中', value: 'active' },
  { label: '已结束', value: 'closed' }, { label: '已过期', value: 'expired' }, { label: '失败', value: 'failed' }
]

function statusLabel(value) { return statusOptions.find(item => item.value === value)?.label || value || '未知' }
function statusType(value) { return ({ active: 'success', closed: 'info', failed: 'danger', expired: 'warning' })[value] || 'primary' }
function formatDuration(value) {
  const seconds = Math.floor(Number(value || 0) / 1000)
  return `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`
}
function getList() {
  loading.value = true
  listVoiceSessions(proxy.addDateRange(queryParams.value, dateRange.value)).then(response => {
    sessionList.value = response.rows || []
    total.value = response.total || 0
  }).finally(() => { loading.value = false })
}
function handleQuery() { queryParams.value.pageNum = 1; getList() }
function resetQuery() { dateRange.value = []; proxy.resetForm('queryRef'); handleQuery() }
getList()
</script>

<style scoped lang="scss">
.assistant-page { background: #f6f8fc; min-height: calc(100vh - 84px); }
.page-heading { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px;
  h2 { margin: 0 0 6px; color: #17213a; } p { margin: 0; color: #7b8499; } }
.filter-card, .table-card { border: 1px solid #e9edf5; border-radius: 14px; }
.filter-card {
  margin-bottom: 16px;
  background: linear-gradient(135deg, #ffffff 0%, #fbfcff 100%);

  :deep(.el-card__body) { padding: 22px 24px 24px; }
  :deep(.el-form-item) { width: 100%; margin-bottom: 0; }
  :deep(.el-form-item__label) {
    height: auto;
    margin-bottom: 8px;
    padding: 0;
    color: #3f4960;
    font-size: 14px;
    font-weight: 600;
    line-height: 22px;
  }
  :deep(.el-input), :deep(.el-select), :deep(.el-date-editor) { width: 100%; }
  :deep(.el-input__wrapper), :deep(.el-select__wrapper) {
    min-height: 40px;
    border-radius: 8px;
    box-shadow: 0 0 0 1px #e4e8f0 inset;
  }
}

.filter-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 20px;
  padding-bottom: 17px;
  border-bottom: 1px solid #edf0f6;
}

.filter-heading-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 5px;

  span { color: #25304a; font-size: 16px; font-weight: 650; }
  small { color: #929bad; font-size: 12px; }
}

.filter-actions {
  display: flex;
  flex: 0 0 auto;
  align-items: center;

  :deep(.el-button) { min-width: 82px; height: 38px; border-radius: 8px; }
}

.filter-grid {
  display: grid;
  grid-template-columns: minmax(210px, 1fr) minmax(180px, .82fr) minmax(220px, 1fr) minmax(360px, 1.45fr);
  gap: 18px 22px;
  align-items: end;
}

.date-item :deep(.el-date-editor) { min-width: 0; }
.account-cell { display: flex; flex-direction: column; gap: 4px; color: #26324d; small { color: #9aa2b4; } }
.muted { color: #9aa2b4; }

@media (max-width: 1280px) {
  .filter-grid { grid-template-columns: repeat(2, minmax(240px, 1fr)); }
}

@media (max-width: 760px) {
  .filter-card-head { align-items: flex-start; flex-direction: column; }
  .filter-actions { width: 100%; }
  .filter-actions :deep(.el-button) { flex: 1; }
  .filter-grid { grid-template-columns: minmax(0, 1fr); }
}
</style>
