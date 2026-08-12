<template>
  <div class="login">
    <div class="login-showcase">
      <div class="showcase-brand">
        <span class="brand-mark"><i></i></span>
        <span class="brand-copy"><strong>天猫智家</strong><small>TMALL SMART HOME</small></span>
      </div>
      <div class="showcase-copy">
        <span class="showcase-label">QWEN3.5 OMNI · REALTIME VOICE</span>
        <h1>让每一次对话<br>更自然、更懂用户</h1>
        <p>语音会话、账号记忆和服务质量，都在一个清晰的运营后台中完成管理。</p>
      </div>
      <div class="login-orb"><div></div><span></span></div>
    </div>
    <div class="login-panel">
    <el-form ref="loginRef" :model="loginForm" :rules="loginRules" class="login-form">
      <div class="form-heading">
        <span>运营管理平台</span>
        <h3>欢迎回来</h3>
        <p>登录后查看语音会话与账号长期记忆</p>
      </div>
      <el-form-item prop="username">
        <el-input
          v-model="loginForm.username"
          type="text"
          size="large"
          auto-complete="off"
          placeholder="账号"
        >
          <template #prefix><svg-icon icon-class="user" class="el-input__icon input-icon" /></template>
        </el-input>
      </el-form-item>
      <el-form-item prop="password">
        <el-input
          v-model="loginForm.password"
          type="password"
          size="large"
          auto-complete="off"
          placeholder="密码"
          @keyup.enter="handleLogin"
        >
          <template #prefix><svg-icon icon-class="password" class="el-input__icon input-icon" /></template>
        </el-input>
      </el-form-item>
      <el-form-item prop="code" v-if="captchaEnabled">
        <el-input
          v-model="loginForm.code"
          size="large"
          auto-complete="off"
          placeholder="验证码"
          style="width: 63%"
          @keyup.enter="handleLogin"
        >
          <template #prefix><svg-icon icon-class="validCode" class="el-input__icon input-icon" /></template>
        </el-input>
        <div class="login-code">
          <img :src="codeUrl" @click="getCode" class="login-code-img"/>
        </div>
      </el-form-item>
      <el-checkbox v-model="loginForm.rememberMe" class="remember-me">30 天内保持登录</el-checkbox>
      <el-form-item style="width:100%;">
        <el-button
          :loading="loading"
          size="large"
          type="primary"
          style="width:100%;"
          @click.prevent="handleLogin"
        >
          <span v-if="!loading">登录运营后台</span>
          <span v-else>正在登录...</span>
        </el-button>
        <div style="float: right;" v-if="register">
          <router-link class="link-type" :to="'/register'">立即注册</router-link>
        </div>
      </el-form-item>
    </el-form>
    <div class="panel-footer">{{ footerContent }}</div>
    </div>
    <!--  底部  -->
    <div class="el-login-footer">
      <span>天猫智家 · 千问智能语音助手</span>
    </div>
  </div>
</template>

<script setup>
import { getCodeImg } from "@/api/login"
import Cookies from "js-cookie"
import { encrypt, decrypt } from "@/utils/jsencrypt"
import useUserStore from '@/store/modules/user'
import defaultSettings from '@/settings'

const footerContent = defaultSettings.footerContent
const userStore = useUserStore()
const route = useRoute()
const router = useRouter()
const { proxy } = getCurrentInstance()

const loginForm = ref({
  username: "",
  password: "",
  rememberMe: false,
  code: "",
  uuid: ""
})

const loginRules = {
  username: [{ required: true, trigger: "blur", message: "请输入您的账号" }],
  password: [{ required: true, trigger: "blur", message: "请输入您的密码" }],
  code: [{ required: true, trigger: "change", message: "请输入验证码" }]
}

const codeUrl = ref("")
const loading = ref(false)
// 验证码开关
const captchaEnabled = ref(true)
// 注册开关
const register = ref(false)
const redirect = ref(undefined)

watch(route, (newRoute) => {
    redirect.value = newRoute.query && newRoute.query.redirect
}, { immediate: true })

function handleLogin() {
  proxy.$refs.loginRef.validate(valid => {
    if (valid) {
      loading.value = true
      // 勾选了需要记住密码设置在 cookie 中设置记住用户名和密码
      if (loginForm.value.rememberMe) {
        Cookies.set("username", loginForm.value.username, { expires: 30 })
        Cookies.set("password", encrypt(loginForm.value.password), { expires: 30 })
        Cookies.set("rememberMe", loginForm.value.rememberMe, { expires: 30 })
      } else {
        // 否则移除
        Cookies.remove("username")
        Cookies.remove("password")
        Cookies.remove("rememberMe")
      }
      // 调用action的登录方法
      userStore.login(loginForm.value).then(() => {
        const query = route.query
        const otherQueryParams = Object.keys(query).reduce((acc, cur) => {
          if (cur !== "redirect") {
            acc[cur] = query[cur]
          }
          return acc
        }, {})
        router.push({ path: redirect.value || "/", query: otherQueryParams })
      }).catch(() => {
        loading.value = false
        // 重新获取验证码
        if (captchaEnabled.value) {
          getCode()
        }
      })
    }
  })
}

function getCode() {
  getCodeImg().then(res => {
    captchaEnabled.value = res.captchaEnabled === undefined ? true : res.captchaEnabled
    if (captchaEnabled.value) {
      codeUrl.value = "data:image/gif;base64," + res.img
      loginForm.value.uuid = res.uuid
    }
  })
}

function getCookie() {
  const username = Cookies.get("username")
  const password = Cookies.get("password")
  const rememberMe = Cookies.get("rememberMe")
  loginForm.value = {
    username: username === undefined ? loginForm.value.username : username,
    password: password === undefined ? loginForm.value.password : decrypt(password),
    rememberMe: rememberMe === undefined ? false : Boolean(rememberMe)
  }
}

getCode()
getCookie()
</script>

<style lang='scss' scoped>
.login {
  display: grid;
  grid-template-columns: minmax(420px, 1.08fr) minmax(420px, .92fr);
  min-height: 100%;
  background: #f6f8fc;
}
.login-showcase {
  position: relative;
  overflow: hidden;
  padding: 54px 7vw;
  color: #fff;
  background: linear-gradient(145deg, #151d48 0%, #303978 54%, #277a9e 100%);
}
.login-showcase::before { content: ''; position: absolute; inset: 0; background: radial-gradient(circle at 72% 28%, rgba(95, 222, 255, .25), transparent 33%); }
.showcase-brand { position: relative; z-index: 2; display: flex; align-items: center; gap: 14px; }
.brand-copy { display:flex; flex-direction:column; align-items:flex-start; line-height:1; strong { font-size:22px; } small { margin-top:7px; color:rgba(201,220,255,.72); font-size:9px; letter-spacing:1.3px; } }
.brand-mark { width:50px; height:50px; display:grid; place-items:center; border-radius:17px 22px 17px 21px; background:radial-gradient(circle at 68% 68%,rgba(91,222,242,.95),transparent 42%),linear-gradient(145deg,#858af6 4%,#659ee9 55%,#51cde8); box-shadow:0 11px 32px rgba(69,197,235,.33); transform:rotate(6deg); i { width:20px; height:20px; background:rgba(255,255,255,.94); border-radius:50%; box-shadow:0 0 16px rgba(255,255,255,.55); } }
.showcase-copy { position: relative; z-index: 2; margin-top: 19vh; max-width: 590px; h1 { margin: 18px 0; font-size: clamp(38px, 4.4vw, 66px); line-height: 1.16; letter-spacing: 2px; } p { max-width: 520px; color: rgba(255,255,255,.68); font-size: 16px; line-height: 1.9; } }
.showcase-label { color:#a6edff; font-size:12px; letter-spacing:2px; }
.login-orb { position:absolute; right:-100px; bottom:-90px; width:420px; height:420px; display:grid; place-items:center; border:1px solid rgba(255,255,255,.08); border-radius:50%; div { width:210px; height:210px; border-radius:50%; background:radial-gradient(circle at 30% 25%,#fff,#d9d9ff 20%,#8298f5 53%,#55cee9); box-shadow:0 0 90px rgba(96,219,255,.45); } span { position:absolute; width:310px; height:310px; border:1px solid rgba(157,231,255,.15); border-radius:50%; } }
.login-panel { display:flex; flex-direction:column; align-items:center; justify-content:center; padding:40px; }
.form-heading { margin-bottom: 30px; span { color:#7580f3; font-size:13px; font-weight:600; } h3 { margin:10px 0 7px; color:#18213a; font-size:30px; } p { margin:0; color:#9aa2b4; } }
.remember-me { margin: 0 0 24px; color:#69738a; }
.panel-footer { margin-top:28px; color:#a3aabc; font-size:12px; }
.el-login-footer { display:none; }

@media (max-width: 900px) {
  .login { grid-template-columns: 1fr; }
  .login-showcase { display:none; }
}

.login-form {
  border-radius: 22px;
  background: #ffffff;
  width: min(440px, 100%);
  padding: 38px 42px 30px;
  box-shadow: 0 22px 65px rgba(47, 61, 112, .1);
  z-index: 1;
  .el-input {
    height: 48px;
    input {
      height: 48px;
    }
  }
  .input-icon {
    width: 18px;
    height: 18px;
    margin: 0 8px 0 1px;
    color: #8a95ab;
  }

  :deep(.el-input__wrapper) {
    padding: 0 15px;
    border-radius: 12px;
  }

  :deep(.el-input__prefix-inner) {
    display: flex;
    align-items: center;
  }
}
.login-tip {
  font-size: 13px;
  text-align: center;
  color: #bfbfbf;
}
.login-code {
  width: 33%;
  height: 40px;
  float: right;
  img {
    cursor: pointer;
    vertical-align: middle;
  }
}
.login-code-img {
  height: 40px;
  padding-left: 12px;
}

html.dark .login {
  background: var(--el-bg-color-page);
  .login-form {
    background: var(--el-bg-color-overlay) !important;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5);
  }
}
</style>
