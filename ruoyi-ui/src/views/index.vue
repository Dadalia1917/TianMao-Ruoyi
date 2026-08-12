<template>
  <div class="assistant-dashboard">
    <section class="hero-card">
      <div class="hero-copy">
        <span class="eyebrow"><i></i> QWEN3.5 OMNI REALTIME</span>
        <h1>千问智能语音助手运营中心</h1>
        <p>集中查看天猫智家的语音会话、账号记忆与消费者使用情况。当前阶段只处理语音与文字，不保存原始录音。</p>
        <div class="hero-actions">
          <el-button type="primary" size="large" @click="go('/assistant/session')">查看语音会话</el-button>
          <el-button size="large" @click="go('/assistant/memory')">管理长期记忆</el-button>
        </div>
      </div>
      <div class="voice-orb" aria-hidden="true"><div class="orb-core"></div><div class="orb-ring ring-one"></div><div class="orb-ring ring-two"></div></div>
    </section>

    <section class="metric-grid" v-loading="loading">
      <article v-for="item in metrics" :key="item.label" class="metric-card">
        <div class="metric-icon" :class="item.tone"><el-icon><component :is="item.icon" /></el-icon></div>
        <div><p>{{ item.label }}</p><strong>{{ item.value }}</strong><span>{{ item.note }}</span></div>
      </article>
    </section>

    <section class="content-grid">
      <el-card shadow="never" class="panel-card recent-panel">
        <template #header><div class="panel-header"><div><h3>最近语音会话</h3><p>实时模型连接与完成情况</p></div><el-button link type="primary" @click="go('/assistant/session')">查看全部</el-button></div></template>
        <el-empty v-if="!recentSessions.length && !loading" description="暂无语音会话" :image-size="84" />
        <div v-else class="session-list">
          <div v-for="session in recentSessions" :key="session.sessionId" class="session-item">
            <div class="session-avatar">{{ accountInitial(session) }}</div>
            <div class="session-main"><strong>{{ session.nickName || session.userName || '匿名设备' }}</strong><span>{{ session.modelName || 'Qwen3.5 Omni' }} · {{ session.startedAt }}</span></div>
            <div class="session-duration">{{ formatDuration(session.durationMs) }}</div>
            <el-tag :type="statusType(session.status)" effect="light">{{ statusLabel(session.status) }}</el-tag>
          </div>
        </div>
      </el-card>

      <el-card shadow="never" class="panel-card readiness-panel">
        <template #header><div class="panel-header"><div><h3>服务构成</h3><p>当前产品能力边界</p></div></div></template>
        <div class="readiness-item ready"><span class="readiness-dot"></span><div><strong>实时语音对话</strong><p>Qwen3.5 Omni · WebSocket 双向音频</p></div><el-tag type="success" effect="plain">已接入</el-tag></div>
        <div class="readiness-item ready"><span class="readiness-dot"></span><div><strong>跨会话长期记忆</strong><p>按登录账号隔离，可审查和删除</p></div><el-tag type="success" effect="plain">已接入</el-tag></div>
        <div class="readiness-item pending"><span class="readiness-dot"></span><div><strong>家居设备控制</strong><p>等待 Home Assistant 与硬件侧接入</p></div><el-tag type="info" effect="plain">后续阶段</el-tag></div>
        <div class="privacy-note"><el-icon><Lock /></el-icon><span>会话仅统计状态、时长和可选文字转录，默认不存储用户原始音频。</span></div>
      </el-card>
    </section>
  </div>
</template>

<script setup name="Index">
import { ChatDotRound, Clock, Collection, UserFilled } from '@element-plus/icons-vue'
import { getAssistantOverview, listVoiceSessions } from '@/api/assistant'

const router = useRouter()
const loading = ref(true)
const overview = ref({})
const recentSessions = ref([])
const metrics = computed(() => [
  { label: '今日语音会话', value: number(overview.value.todaySessions), note: `累计 ${number(overview.value.totalSessions)} 次`, icon: ChatDotRound, tone: 'blue' },
  { label: '累计对话时长', value: formatHours(overview.value.totalDurationMs), note: '基于已结束会话统计', icon: Clock, tone: 'violet' },
  { label: '有效长期记忆', value: number(overview.value.activeMemories), note: '跨语音会话持续生效', icon: Collection, tone: 'cyan' },
  { label: '已有记忆账号', value: number(overview.value.memoryUsers), note: `今日失败 ${number(overview.value.todayFailures)} 次`, icon: UserFilled, tone: 'rose' }
])

function number(value) { return Number(value || 0).toLocaleString('zh-CN') }
function formatHours(value) { return `${(Number(value || 0) / 3600000).toFixed(1)} 小时` }
function formatDuration(value) {
  const seconds = Math.floor(Number(value || 0) / 1000)
  return `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`
}
function statusLabel(value) { return ({ connecting: '连接中', active: '对话中', closed: '已结束', expired: '已过期', failed: '失败' })[value] || '未知' }
function statusType(value) { return ({ active: 'success', closed: 'info', expired: 'warning', failed: 'danger' })[value] || 'primary' }
function accountInitial(session) { return (session.nickName || session.userName || '匿').slice(0, 1).toUpperCase() }
function go(path) { router.push(path) }

Promise.all([getAssistantOverview(), listVoiceSessions({ pageNum: 1, pageSize: 6 })]).then(([summary, sessions]) => {
  overview.value = summary.data || {}
  recentSessions.value = sessions.rows || []
}).finally(() => { loading.value = false })
</script>

<style scoped lang="scss">
.assistant-dashboard { min-height: calc(100vh - 84px); padding: 26px; background: #f5f7fb; color: #182039; }
.hero-card { position: relative; min-height: 272px; overflow: hidden; display: flex; align-items: center; justify-content: space-between; padding: 42px 56px; border-radius: 24px; background: linear-gradient(125deg, #18214b 0%, #313b7c 45%, #2576a3 100%); box-shadow: 0 18px 50px rgba(34, 53, 116, .18); }
.hero-card::before { content: ''; position: absolute; inset: 0; background: radial-gradient(circle at 72% 20%, rgba(107, 238, 255, .2), transparent 34%); }
.hero-copy { position: relative; z-index: 2; width: min(700px, 62%); color: #fff; h1 { margin: 13px 0 14px; font-size: 34px; letter-spacing: 1px; } p { margin: 0; max-width: 640px; color: rgba(255,255,255,.72); line-height: 1.8; font-size: 15px; } }
.eyebrow { font-size: 12px; letter-spacing: 2px; color: #a9ecff; i { display: inline-block; width: 7px; height: 7px; margin-right: 8px; border-radius: 50%; background: #4ee4bc; box-shadow: 0 0 12px #4ee4bc; } }
.hero-actions { margin-top: 26px; :deep(.el-button--primary) { background: linear-gradient(120deg, #7c83ff, #53c7eb); border: 0; } :deep(.el-button:not(.el-button--primary)) { color: #fff; border-color: rgba(255,255,255,.24); background: rgba(255,255,255,.08); } }
.voice-orb { position: relative; z-index: 1; width: 230px; height: 230px; margin-right: 48px; display: grid; place-items: center; }
.orb-core { width: 145px; height: 145px; border-radius: 50%; background: radial-gradient(circle at 35% 28%, #fff 0, #d9dcff 18%, #8c9cff 48%, #59cbe8 83%); box-shadow: 0 0 60px rgba(107, 222, 255, .5), inset -16px -18px 32px rgba(69, 78, 190, .24); animation: float 4s ease-in-out infinite; }
.orb-ring { position: absolute; border: 1px solid rgba(158,235,255,.25); border-radius: 50%; }.ring-one { width: 190px; height: 190px; }.ring-two { width: 225px; height: 225px; }
.metric-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; margin: 22px 0; min-height: 126px; }
.metric-card { display: flex; align-items: center; gap: 18px; min-width: 0; padding: 24px; border: 1px solid #e9edf5; border-radius: 18px; background: #fff; box-shadow: 0 8px 26px rgba(52,65,111,.05); }
.metric-icon { flex: 0 0 48px; height: 48px; display: grid; place-items: center; border-radius: 14px; font-size: 23px; &.blue { color:#617af7; background:#eef1ff; } &.violet { color:#996bec; background:#f4edff; } &.cyan { color:#24a8c2; background:#e7fafd; } &.rose { color:#e46c91; background:#fff0f4; } }
.metric-card div:last-child { min-width: 0; display: grid; grid-template-columns: auto 1fr; gap: 5px 10px; align-items: baseline; p { grid-column: 1 / -1; margin:0; color:#7c8599; } strong { font-size: 26px; color:#17213a; } span { color:#a0a7b7; font-size:12px; } }
.content-grid { display: grid; grid-template-columns: minmax(0, 1.55fr) minmax(360px, .85fr); gap: 18px; }
.panel-card { border: 1px solid #e9edf5; border-radius: 18px; :deep(.el-card__header) { padding: 22px 24px 15px; border-bottom: 0; } :deep(.el-card__body) { padding: 6px 24px 22px; } }
.panel-header { display:flex; justify-content:space-between; align-items:center; h3 { margin:0 0 4px; font-size:18px; } p { margin:0; color:#9aa2b3; font-size:13px; } }
.session-item { display:grid; grid-template-columns: 44px minmax(0,1fr) 70px 74px; align-items:center; gap:14px; padding:14px 0; border-bottom:1px solid #f0f2f7; &:last-child { border-bottom:0; } }
.session-avatar { width:42px; height:42px; display:grid; place-items:center; border-radius:13px; color:#fff; font-weight:700; background:linear-gradient(135deg,#7d84f6,#51c6e7); }
.session-main { min-width:0; display:flex; flex-direction:column; gap:5px; strong { color:#26304a; } span { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:#9aa2b4; font-size:12px; } }.session-duration { color:#5b657b; font-variant-numeric:tabular-nums; }
.readiness-item { display:grid; grid-template-columns:10px minmax(0,1fr) auto; align-items:center; gap:12px; padding:14px 0; border-bottom:1px solid #f0f2f7; strong { color:#2b354d; } p { margin:5px 0 0; color:#969fb2; font-size:12px; } }.readiness-dot { width:8px; height:8px; border-radius:50%; background:#57d7b3; }.pending .readiness-dot { background:#b8bfce; }
.privacy-note { display:flex; gap:10px; margin-top:18px; padding:14px; border-radius:12px; color:#687389; background:#f5f7fb; font-size:13px; line-height:1.6; }
@keyframes float { 50% { transform: translateY(-9px) scale(1.02); } }
@media (max-width: 1200px) { .metric-grid { grid-template-columns:repeat(2,1fr); }.content-grid { grid-template-columns:1fr; }.voice-orb { margin-right:0; } }
@media (max-width: 760px) { .assistant-dashboard { padding:16px; }.hero-card { padding:30px; }.hero-copy { width:100%; h1 { font-size:28px; } }.voice-orb { display:none; }.metric-grid { grid-template-columns:1fr; } }
</style>
