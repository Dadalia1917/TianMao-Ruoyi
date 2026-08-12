<template>
  <view class="agreement-page">
    <view class="ambient ambient-one"></view>
    <view class="ambient ambient-two"></view>
    <view class="document-card">
      <view class="document-head">
        <view class="brand-mark"><view class="brand-core"></view></view>
        <text class="document-title">{{ document.title }}</text>
        <text class="document-meta">更新日期：2026年8月11日　生效日期：2026年8月11日</text>
      </view>

      <view class="notice-card">
        <text class="notice-title">请您重点阅读</text>
        <text class="notice-text">{{ document.notice }}</text>
      </view>

      <view class="intro-block">
        <text v-for="(paragraph, index) in document.intro" :key="`intro-${index}`" class="paragraph">{{ paragraph }}</text>
      </view>

      <view v-for="(section, sectionIndex) in document.sections" :key="section.title" class="section">
        <text class="section-title">{{ sectionIndex + 1 }}. {{ section.title }}</text>
        <text v-for="(paragraph, index) in section.paragraphs" :key="`p-${sectionIndex}-${index}`" class="paragraph">{{ paragraph }}</text>
        <view v-if="section.items && section.items.length" class="item-list">
          <view v-for="(item, index) in section.items" :key="`i-${sectionIndex}-${index}`" class="item-row">
            <text class="item-dot">•</text>
            <text class="item-text">{{ item }}</text>
          </view>
        </view>
      </view>

      <view class="contact-card">
        <text class="contact-title">联系我们</text>
        <text class="contact-text">服务提供者：无锡捷普迅智能科技有限公司</text>
        <text class="contact-text">如对本协议或个人信息处理有疑问，请通过产品说明、应用安装渠道或服务合同中公布的运营方联系方式与我们联系。我们将在核实身份后依法处理。</text>
      </view>
      <text class="footer-note">天猫智家 · TMALL SMART HOME</text>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'

const agreementType = ref('service')

const documents = {
  service: {
    title: '天猫智家用户服务协议',
    notice: '本服务包含人工智能生成内容。Qwen 等模型并非真人，其回答可能不准确，也不能替代医疗、法律、金融等专业意见。当前版本尚未接入家庭设备控制，AI 不会实际操作您的家具或电器。',
    intro: [
      '欢迎使用天猫智家语音助手（以下简称“本服务”）。本服务由无锡捷普迅智能科技有限公司（以下简称“我们”）提供。请在注册、登录或使用前认真阅读本协议，尤其是加粗提示或涉及您重要权益的内容。',
      '当您注册、登录、勾选同意或实际使用本服务，即表示您已阅读、理解并同意本协议。如您不同意，请停止注册或使用。'
    ],
    sections: [
      {
        title: '服务范围',
        paragraphs: ['本服务现阶段提供账号登录、Qwen3.5 Omni 实时语音对话、文字对话、会话记录和长期记忆等功能。后续如接入 Home Assistant 或智能家居控制，我们会在启用前另行说明所需权限、设备范围和操作风险。'],
        items: []
      },
      {
        title: '账号注册与安全',
        paragraphs: ['您应提供真实、合法且必要的注册信息，妥善保管账号和密码，并对账号下的操作负责。发现账号被冒用或存在异常时，请及时联系我们。为改善使用体验，应用可在本地保存登录状态；连续30天未打开应用后，身份状态将过期并要求重新登录。'],
        items: []
      },
      {
        title: '语音与人工智能服务',
        paragraphs: ['获得麦克风授权后，您的语音将通过网络实时传输至服务端及阿里云百炼/千问模型完成识别与回复。您可以随时静音、结束对话或在系统设置中撤回麦克风权限。撤回后，语音功能将无法使用，但不影响可独立使用的其他功能。'],
        items: [
          'AI 生成内容可能存在事实错误、遗漏、偏差或不适宜内容，请结合实际情况判断。',
          '涉及人身、财产、健康或其他重要决定时，请咨询具备资质的专业人员。',
          '您不得利用本服务生成、传播违法有害内容，或侵害他人隐私、知识产权和合法权益。'
        ]
      },
      {
        title: '会话记录与长期记忆',
        paragraphs: ['为保持跨会话体验，本服务可保存对话记录，并从对话中提取您主动表达的稳定偏好、称呼等信息形成长期记忆。记录和记忆按登录账号隔离。您可以在应用内查看和删除长期记忆、删除会话或清空本机记录。'],
        items: []
      },
      {
        title: '用户行为规范',
        paragraphs: ['您应依法、文明、诚信使用本服务，不得攻击系统、绕过安全措施、批量滥用接口、冒用他人身份，或输入、生成和传播法律法规禁止的内容。因违反本协议造成损失的，您应依法承担相应责任。'],
        items: []
      },
      {
        title: '知识产权',
        paragraphs: ['本应用的软件、界面、标识和相关技术成果受法律保护。您对自行输入且依法享有权利的内容保留相应权利；AI 生成内容的权利归属与使用限制依适用法律、模型服务规则及内容来源确定。请勿将可能侵权的生成内容用于商业传播。'],
        items: []
      },
      {
        title: '服务变更与中断',
        paragraphs: ['因网络、设备、模型服务维护、不可抗力或安全风险，服务可能暂时中断。我们会在合理范围内保障服务连续性，并对重大功能或规则变化以应用内提示等方式告知。'],
        items: []
      },
      {
        title: '未成年人保护',
        paragraphs: ['未满14周岁的未成年人应在监护人陪同和同意下使用。监护人应指导未成年人合理使用人工智能服务，避免过度依赖，并关注其输入和接收的内容。'],
        items: []
      },
      {
        title: '协议更新与争议解决',
        paragraphs: ['我们可能根据业务或法律要求更新本协议。涉及您重大权益的变更会以显著方式提示。协议适用中华人民共和国法律；如发生争议，双方应先友好协商，协商不成的，可依法向有管辖权的人民法院提起诉讼。'],
        items: []
      }
    ]
  },
  privacy: {
    title: '天猫智家隐私政策',
    notice: '使用实时语音时，麦克风音频会发送至云端进行识别和生成回复。当前配置默认不持久化保存原始音频；会话文字、长期记忆及必要运行日志会按本政策处理。',
    intro: [
      '无锡捷普迅智能科技有限公司重视您的个人信息和隐私安全。本政策说明天猫智家语音助手如何收集、使用、存储、共享和保护个人信息，以及您如何行使相关权利。',
      '我们遵循合法、正当、必要和诚信原则，仅处理实现功能所需的信息。若某项功能需要处理额外信息，我们会在启用前另行告知并依法取得授权。'
    ],
    sections: [
      {
        title: '我们收集的信息',
        paragraphs: ['不同功能所需信息不同。您可以选择不提供非必要信息，但对应功能可能无法使用。'],
        items: [
          '账号信息：用户名、用户ID、昵称、登录令牌和登录有效期，用于身份认证、账号隔离和安全管理。',
          '语音交互信息：麦克风采集的实时音频、语音转写文本、模型回复和会话状态，用于完成实时对话。当前默认不持久化保存原始音频。',
          '文字对话信息：您输入的问题、模型回复、所选模型及会话上下文，用于提供连续对话和保存记录。',
          '长期记忆：从对话中提取的称呼、偏好等稳定信息，用于在不同会话间提供连贯体验。',
          '设备与运行信息：会话ID、IP地址、浏览器或设备类型、网络状态、错误日志、连接时长，用于安全防护、故障排查和服务优化。',
          '本地存储信息：登录令牌、最近活跃时间和本机对话记录，用于保持登录状态和展示历史。'
        ]
      },
      {
        title: '麦克风权限',
        paragraphs: ['仅在您启用语音对话时申请和使用麦克风权限。您可通过应用静音/结束按钮或系统权限设置停止采集。拒绝或撤回权限后，实时语音功能无法使用，您仍可使用文字对话等不依赖麦克风的功能。请避免在非必要情况下说出身份证号、银行卡号、精确住址等敏感信息。'],
        items: []
      },
      {
        title: '信息使用目的',
        paragraphs: ['我们将上述信息用于账号登录与安全校验、提供语音和文字对话、展示历史记录、形成您授权使用的跨会话记忆、排查故障、防范滥用，以及履行法律法规规定的义务。未经另行同意，我们不会将信息用于与上述目的无关的用途。'],
        items: []
      },
      {
        title: '委托处理与第三方服务',
        paragraphs: ['为完成模型推理，语音、转写文本或文字问题会经我们的服务端发送至阿里云百炼/DashScope 及所选 Qwen、DeepSeek 等模型服务。相关服务商按照我们的指示和其适用规则处理数据。正式上线前，我们将根据实际部署地区、供应商配置和数据保留策略更新本节。'],
        items: []
      },
      {
        title: '存储期限与位置',
        paragraphs: ['我们在实现目的所需的最短期限内保存信息。原始语音当前仅用于实时传输和播放，默认不落库；会话记录和长期记忆保存至您删除、注销账号或不再需要为止；安全与运行日志按合理运维周期保存。本机数据可通过清空记录、退出登录或卸载应用清除。正式部署时，数据存储地点以运营方实际服务器配置为准。'],
        items: []
      },
      {
        title: '共享、转让与公开披露',
        paragraphs: ['除为实现功能所必需的委托处理、取得您的单独同意或法律法规另有规定外，我们不会向其他主体共享个人信息。发生合并、分立、资产转让等情形时，我们会告知接收方并要求其继续履行个人信息保护义务。我们不会公开披露您的个人信息，法律另有规定或取得单独同意的除外。'],
        items: []
      },
      {
        title: '您的权利',
        paragraphs: ['您有权依法查询、复制、更正、补充或删除个人信息，并可撤回授权。您可以在“管家记忆”中查看和删除长期记忆，在会话列表删除记录或清空本机记录，在系统设置中撤回麦克风权限。账号注销或其他无法在页面完成的请求，可通过运营方公布的客服渠道联系我们。'],
        items: []
      },
      {
        title: '信息安全',
        paragraphs: ['我们采取访问控制、账号隔离、传输保护、日志审计和最小权限等措施保护信息。互联网环境无法保证绝对安全；发生可能影响您权益的安全事件时，我们会依法采取补救措施并按规定告知。'],
        items: []
      },
      {
        title: '未成年人信息',
        paragraphs: ['未满14周岁的未成年人应由监护人阅读本政策并同意后使用。若我们发现未经监护人同意处理了儿童个人信息，将依法尽快删除或匿名化处理。'],
        items: []
      },
      {
        title: '政策更新',
        paragraphs: ['我们可能根据功能和法律变化更新本政策。涉及处理目的、方式、信息种类或您权利的重大变化时，我们会通过弹窗、页面提示等显著方式重新告知，并在依法需要时再次取得同意。'],
        items: []
      }
    ]
  }
}

const document = computed(() => documents[agreementType.value] || documents.service)

onLoad((options) => {
  agreementType.value = options && options.type === 'privacy' ? 'privacy' : 'service'
  uni.setNavigationBarTitle({ title: agreementType.value === 'privacy' ? '隐私政策' : '用户服务协议' })
})
</script>

<style lang="scss" scoped>
.agreement-page {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  box-sizing: border-box;
  padding: 32rpx 24rpx calc(64rpx + env(safe-area-inset-bottom));
  background: linear-gradient(155deg, #f8faff 0%, #ffffff 46%, #f6f5ff 100%);
  color: #343640;
}

.ambient { position: fixed; z-index: 0; border-radius: 50%; filter: blur(28rpx); pointer-events: none; }
.ambient-one { width: 420rpx; height: 420rpx; right: -220rpx; top: 80rpx; background: rgba(76, 203, 235, .12); }
.ambient-two { width: 360rpx; height: 360rpx; left: -200rpx; bottom: 20rpx; background: rgba(139, 128, 245, .10); }

.document-card {
  position: relative;
  z-index: 1;
  max-width: 1080rpx;
  margin: 0 auto;
  padding: 48rpx 38rpx 56rpx;
  box-sizing: border-box;
  border: 1px solid rgba(229, 232, 241, .92);
  border-radius: 30rpx;
  background: rgba(255, 255, 255, .92);
  box-shadow: 0 20rpx 60rpx rgba(52, 61, 97, .07);
}

.document-head { display: flex; flex-direction: column; align-items: center; padding-bottom: 34rpx; border-bottom: 1px solid #eef0f5; }
.brand-mark { position: relative; width: 68rpx; height: 68rpx; border-radius: 23rpx; transform: rotate(7deg); background: linear-gradient(145deg, #8982f4, #4ecaea); box-shadow: 0 12rpx 28rpx rgba(93, 119, 214, .18); }
.brand-core { position: absolute; width: 26rpx; height: 26rpx; left: 21rpx; top: 21rpx; border-radius: 50%; background: rgba(255,255,255,.92); }
.document-title { margin-top: 24rpx; text-align: center; font-size: 38rpx; line-height: 1.4; font-weight: 650; color: #252832; }
.document-meta { margin-top: 12rpx; text-align: center; font-size: 21rpx; color: #9da1ad; }

.notice-card { margin: 34rpx 0 38rpx; padding: 28rpx 30rpx; border-radius: 22rpx; border: 1px solid #e7e4ff; background: linear-gradient(135deg, #f6f3ff, #f2faff); }
.notice-title { display: block; font-size: 25rpx; font-weight: 620; color: #6564b5; }
.notice-text { display: block; margin-top: 12rpx; font-size: 24rpx; line-height: 1.8; color: #666a78; }
.intro-block { margin-bottom: 36rpx; }
.section { margin-top: 38rpx; }
.section-title { display: block; margin-bottom: 16rpx; font-size: 30rpx; line-height: 1.5; font-weight: 650; color: #292c36; }
.paragraph { display: block; margin-top: 12rpx; font-size: 25rpx; line-height: 1.9; text-align: justify; color: #555967; }
.item-list { margin: 14rpx 0 0 8rpx; }
.item-row { display: flex; align-items: flex-start; margin-top: 12rpx; }
.item-dot { flex: none; width: 28rpx; font-size: 26rpx; line-height: 1.8; color: #7977df; }
.item-text { flex: 1; font-size: 25rpx; line-height: 1.8; color: #555967; }
.contact-card { margin-top: 48rpx; padding: 28rpx 30rpx; border-radius: 22rpx; background: #f7f8fb; }
.contact-title { display: block; margin-bottom: 10rpx; font-size: 27rpx; font-weight: 650; color: #343742; }
.contact-text { display: block; margin-top: 8rpx; font-size: 23rpx; line-height: 1.8; color: #656977; }
.footer-note { display: block; margin-top: 42rpx; text-align: center; font-size: 19rpx; letter-spacing: 2rpx; color: #afb2bd; }

@media screen and (min-width: 900px) {
  .agreement-page { padding: 40px; }
  .document-card { max-width: 980px; padding: 48px 68px 56px; border-radius: 24px; }
  .brand-mark { width: 52px; height: 52px; border-radius: 17px; }
  .brand-core { width: 20px; height: 20px; left: 16px; top: 16px; }
  .document-title { margin-top: 18px; font-size: 28px; }
  .document-meta { margin-top: 8px; font-size: 13px; }
  .notice-card { margin: 28px 0 34px; padding: 22px 26px; border-radius: 18px; }
  .notice-title { font-size: 16px; }
  .notice-text, .paragraph, .item-text { font-size: 15px; }
  .section { margin-top: 30px; }
  .section-title { margin-bottom: 10px; font-size: 20px; }
  .contact-title { font-size: 17px; }
  .contact-text { font-size: 14px; }
}
</style>
