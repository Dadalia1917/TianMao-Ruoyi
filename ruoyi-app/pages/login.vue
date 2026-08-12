<template>
  <view class="normal-login-container">
    <view class="login-ambient ambient-top"></view>
    <view class="login-ambient ambient-bottom"></view>
    <view class="logo-content">
      <view class="login-logo"><view class="login-logo-core"></view></view>
      <text class="title">天猫智家语音助手</text>
      <text class="subtitle">Tmall Smart Home Voice Assistant</text>
    </view>
    <view class="login-form-content">
      <view v-if="expiredHint" class="expired-hint">已超过 30 天未打开应用，请重新登录</view>
      <text class="form-title">欢迎回来</text>
      <text class="form-subtitle">登录后将直接进入您的智能语音助手</text>
      <view class="input-item flex align-center">
        <view class="iconfont icon-user icon"></view>
        <input v-model="loginForm.username" class="input" type="text" placeholder="请输入账号" maxlength="30" />
      </view>
      <view class="input-item flex align-center">
        <view class="iconfont icon-password icon"></view>
        <input v-model="loginForm.password" type="password" class="input" placeholder="请输入密码" maxlength="20" />
      </view>
      <view class="input-item captcha-item flex align-center" v-if="captchaEnabled">
        <view class="iconfont icon-code icon"></view>
        <input v-model="loginForm.code" type="number" class="input" placeholder="请输入验证码" maxlength="4" />
        <view class="login-code"> 
          <image :src="codeUrl" @click="getCode" class="login-code-img"></image>
        </view>
      </view>
      <view class="action-btn">
        <button @click="handleLogin" class="login-btn">登录并进入语音助手</button>
      </view>
      <view class="reg text-center" v-if="register">
        <text class="text-grey1">没有账号？</text>
        <text @click="handleUserRegister" class="text-blue">立即注册</text>
      </view>
      <view class="xieyi text-center">
        <text class="text-grey1">登录即代表同意</text>
        <text @click="handleUserAgrement" class="text-blue">《用户协议》</text>
        <text @click="handlePrivacy" class="text-blue">《隐私政策》</text>
      </view>
    </view>
     
  </view>
</template>

<script setup>
  import { ref, getCurrentInstance } from "vue"
  import { onLoad } from  "@dcloudio/uni-app"
  import { hasValidLocalSession } from '@/utils/auth'
  import { getCodeImg } from '@/api/login'
  import { useUserStore } from '@/store'

  const { proxy } = getCurrentInstance()
  const codeUrl = ref("")
  // 验证码开关
  const captchaEnabled = ref(true)
  // 用户注册开关
  const register = ref(true)
  const expiredHint = ref(false)
  const loginForm = ref({
    username: "",
    password: "",
    code: "",
    uuid: ""
  })

  // 用户注册
  function handleUserRegister() {
    proxy.$tab.redirectTo(`/pages/register`)
  }

  // 隐私协议
  function handlePrivacy() {
    proxy.$tab.navigateTo('/pages/common/agreement/index?type=privacy')
  }

  // 用户协议
  function handleUserAgrement() {
    proxy.$tab.navigateTo('/pages/common/agreement/index?type=service')
  }

  // 获取图形验证码
  function getCode() {
    getCodeImg().then(res => {
      captchaEnabled.value = res.captchaEnabled === undefined ? true : res.captchaEnabled
        if (captchaEnabled.value) {
          codeUrl.value = 'data:image/gif;base64,' + res.img
          loginForm.value.uuid = res.uuid
        }
    })
  }

  // 登录方法
  async function handleLogin() {
    if (loginForm.value.username === "") {
      proxy.$modal.msgError("请输入账号")
    } else if (loginForm.value.password === "") {
      proxy.$modal.msgError("请输入密码")
    } else if (loginForm.value.code === "" && captchaEnabled.value) {
      proxy.$modal.msgError("请输入验证码")
    } else {
      proxy.$modal.loading("登录中，请耐心等待...")
      pwdLogin()
    }
  }

  // 密码登录
  async function pwdLogin() {
    useUserStore().login(loginForm.value).then(() => {
      proxy.$modal.closeLoading()
      loginSuccess()
    }).catch(() => {
      proxy.$modal.closeLoading()
      if (captchaEnabled.value) {
        getCode()
      }
    })
  }

  // 登录成功后，处理函数
  function loginSuccess(result) {
    // 设置用户信息
    useUserStore().getInfo().then(res => {
      proxy.$tab.reLaunch('/pages/index')
    })
  }

  onLoad((options) => {
    expiredHint.value = options && options.reason === 'expired'
    //#ifdef H5
    if (hasValidLocalSession()) {
      proxy.$tab.reLaunch('/pages/index')
    }
    //#endif
  })

  getCode()
</script>

<style lang="scss" scoped>
  page {
    background-color: #ffffff;
  }

  .normal-login-container {
    width: 100%;

    .logo-content {
      width: 100%;
      font-size: 21px;
      text-align: center;
      padding-top: 15%;

      image {
        border-radius: 4px;
      }

      .title {
        margin-left: 10px;
      }
    }

    .login-form-content {
      text-align: center;
      margin: 20px auto;
      margin-top: 15%;
      width: 80%;

      .input-item {
        margin: 20px auto;
        background-color: #f5f6f7;
        height: 45px;
        border-radius: 20px;

        .icon {
          font-size: 38rpx;
          margin-left: 10px;
          color: #999;
        }

        .input {
          width: 100%;
          font-size: 14px;
          line-height: 20px;
          text-align: left;
          padding-left: 15px;
        }

      }

      .login-btn {
        margin-top: 40px;
        height: 45px;
      }
      
      .reg {
        margin-top: 15px;
      }
      
      .xieyi {
        color: #333;
        margin-top: 20px;
      }
      
      .login-code {
        height: 38px;
        float: right;
      
        .login-code-img {
          height: 38px;
          position: absolute;
          margin-left: 10px;
          width: 200rpx;
        }
      }
    }
  }
</style>

<style lang="scss" scoped>
  .normal-login-container {
    position: relative;
    min-height: 100vh;
    box-sizing: border-box;
    overflow: hidden;
    padding: calc(var(--status-bar-height) + 70rpx) 52rpx calc(44rpx + env(safe-area-inset-bottom));
    background: linear-gradient(155deg, #fafbff 0%, #fff 48%, #f7f5ff 100%);
  }

  .login-ambient { position: absolute; border-radius: 50%; filter: blur(18rpx); pointer-events: none; }
  .ambient-top { width: 480rpx; height: 480rpx; top: -260rpx; right: -230rpx; background: rgba(77, 207, 237, 0.15); }
  .ambient-bottom { width: 420rpx; height: 420rpx; bottom: -260rpx; left: -210rpx; background: rgba(157, 127, 245, 0.13); }

  .normal-login-container .logo-content {
    position: relative;
    z-index: 2;
    width: 100%;
    padding-top: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .login-logo {
    position: relative;
    width: 114rpx;
    height: 114rpx;
    border-radius: 38rpx;
    background: linear-gradient(145deg, #8b83f5, #4acbea);
    box-shadow: 0 20rpx 44rpx rgba(95, 121, 218, 0.23);
    transform: rotate(8deg);
  }

  .login-logo-core { position: absolute; width: 48rpx; height: 48rpx; left: 33rpx; top: 33rpx; border-radius: 50%; background: rgba(255,255,255,.9); box-shadow: 18rpx -15rpx 30rpx rgba(255,255,255,.65); }
  .normal-login-container .logo-content .title { margin: 32rpx 0 0; font-size: 38rpx; font-weight: 650; letter-spacing: 2rpx; color: #292b36; }
  .subtitle { margin-top: 10rpx; font-size: 18rpx; letter-spacing: 1.5rpx; color: #a3a6b2; }

  .normal-login-container .login-form-content {
    position: relative;
    z-index: 2;
    width: 100%;
    max-width: 680rpx;
    margin: 70rpx auto 0;
    padding: 42rpx 34rpx 34rpx;
    box-sizing: border-box;
    border: 1px solid rgba(231,232,240,.88);
    border-radius: 38rpx;
    background: rgba(255,255,255,.82);
    box-shadow: 0 24rpx 70rpx rgba(61,66,102,.08);
    backdrop-filter: blur(16rpx);
  }

  .form-title { display: block; text-align: left; font-size: 34rpx; font-weight: 620; color: #30323c; }
  .form-subtitle { display: block; margin-top: 10rpx; text-align: left; font-size: 22rpx; color: #a0a2ad; }
  .expired-hint { margin-bottom: 24rpx; padding: 17rpx 20rpx; border-radius: 17rpx; text-align: left; font-size: 21rpx; color: #b56472; background: #fff1f3; }

  .normal-login-container .login-form-content .input-item {
    width: 100%;
    height: 90rpx;
    margin: 24rpx 0 0;
    border: 1px solid #ececf3;
    border-radius: 24rpx;
    background: #f8f9fc;
  }

  .normal-login-container .login-form-content .input-item .input { font-size: 26rpx; color: #333540; }
  .normal-login-container .login-form-content .captcha-item { position: relative; padding-right: 205rpx; box-sizing: border-box; }
  .normal-login-container .login-form-content .captcha-item .login-code { position: absolute; right: 8rpx; top: 7rpx; width: 190rpx; height: 74rpx; overflow: hidden; border-radius: 18rpx; }
  .normal-login-container .login-form-content .captcha-item .login-code-img { position: static; width: 190rpx; height: 74rpx; margin: 0; }
  .normal-login-container .login-form-content .login-btn { height: 90rpx; margin-top: 36rpx; border-radius: 26rpx; line-height: 90rpx; font-size: 27rpx; color: #fff; background: linear-gradient(135deg, #817df1, #56c9e9); box-shadow: 0 16rpx 36rpx rgba(96,119,215,.2); }
  .normal-login-container .login-form-content .login-btn::after { border: none; }
  .normal-login-container .login-form-content .reg { margin-top: 28rpx; font-size: 23rpx; }
  .normal-login-container .login-form-content .xieyi { margin-top: 28rpx; font-size: 20rpx; }

  @media screen and (min-width: 900px) {
    .normal-login-container { padding-top: 55px; }
    .login-logo { width: 72px; height: 72px; border-radius: 24px; }
    .login-logo-core { width: 30px; height: 30px; left: 21px; top: 21px; }
    .normal-login-container .logo-content .title { margin-top: 20px; font-size: 25px; }
    .subtitle { margin-top: 7px; font-size: 11px; }
    .normal-login-container .login-form-content { width: 430px; margin-top: 36px; padding: 28px 28px 24px; border-radius: 24px; }
    .form-title { font-size: 22px; }
    .form-subtitle { margin-top: 6px; font-size: 13px; }
    .normal-login-container .login-form-content .input-item { height: 52px; margin-top: 16px; border-radius: 16px; }
    .normal-login-container .login-form-content .login-btn { height: 52px; margin-top: 24px; border-radius: 16px; line-height: 52px; font-size: 15px; }
  }
</style>
