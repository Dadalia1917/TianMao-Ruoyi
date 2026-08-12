<template>
  <view class="normal-login-container">
    <view class="login-ambient ambient-top"></view>
    <view class="login-ambient ambient-bottom"></view>
    <view class="logo-content">
      <view class="login-logo"><view class="login-logo-core"></view></view>
      <text class="title">注册天猫智家账号</text>
      <text class="subtitle">创建属于您的智能语音空间</text>
    </view>
    <view class="login-form-content">
      <text class="form-title">创建账号</text>
      <text class="form-subtitle">注册一次，之后 30 天内打开应用无需重复登录</text>
      <view class="input-item flex align-center">
        <view class="iconfont icon-user icon"></view>
        <input v-model="registerForm.username" class="input" type="text" placeholder="请输入账号" maxlength="30" />
      </view>
      <view class="input-item flex align-center">
        <view class="iconfont icon-password icon"></view>
        <input v-model="registerForm.password" type="password" class="input" placeholder="请输入密码" maxlength="20" />
      </view>
      <view class="input-item flex align-center">
        <view class="iconfont icon-password icon"></view>
        <input v-model="registerForm.confirmPassword" type="password" class="input" placeholder="请输入重复密码" maxlength="20" />
      </view>
      <view class="input-item captcha-item flex align-center" v-if="captchaEnabled">
        <view class="iconfont icon-code icon"></view>
        <input v-model="registerForm.code" type="number" class="input" placeholder="请输入验证码" maxlength="4" />
        <view class="login-code"> 
          <image :src="codeUrl" @click="getCode" class="login-code-img"></image>
        </view>
      </view>
      <view class="action-btn">
        <button @click="handleRegister()" class="register-btn">注册账号</button>
      </view>
    </view>
    <view class="xieyi text-center">
      <text @click="handleUserLogin" class="text-blue">使用已有账号登录</text>
    </view>
  </view>
</template>

<script setup>
  import { getCodeImg, register } from '@/api/login'
  import { ref, getCurrentInstance } from "vue"

  const { proxy } = getCurrentInstance()
  const codeUrl = ref("")
  // 验证码开关
  const captchaEnabled = ref(true)
  const registerForm = ref({
    username: "",
    password: "",
    confirmPassword: "",
    code: "",
    uuid: ""
  })

  // 用户登录
  function handleUserLogin() {
    proxy.$tab.navigateTo(`/pages/login`)
  }

  // 获取图形验证码
  function getCode() {
    getCodeImg().then(res => {
      captchaEnabled.value = res.captchaEnabled === undefined ? true : res.captchaEnabled
        if (captchaEnabled.value) {
          codeUrl.value = 'data:image/gif;base64,' + res.img
          registerForm.value.uuid = res.uuid
      }
    })
  }

  // 注册方法
  async function handleRegister() {
    if (registerForm.value.username === "") {
      proxy.$modal.msgError("请输入您的账号")
    } else if (registerForm.value.password === "") {
      proxy.$modal.msgError("请输入您的密码")
    } else if (registerForm.value.confirmPassword === "") {
      proxy.$modal.msgError("请再次输入您的密码")
    } else if (registerForm.value.password !== registerForm.value.confirmPassword) {
      proxy.$modal.msgError("两次输入的密码不一致")
    } else if (registerForm.value.code === "" && captchaEnabled.value) {
      proxy.$modal.msgError("请输入验证码")
    } else {
      proxy.$modal.loading("注册中，请耐心等待...")
      userRegister()
    }
  }

  // 用户注册
  async function userRegister() {
    register(registerForm.value).then(res => {
      proxy.$modal.closeLoading()
      uni.showModal({
        title: "系统提示",
        content: "恭喜你，您的账号 " + registerForm.value.username + " 注册成功！",
        success: function (res) {
          if (res.confirm) {
            uni.redirectTo({ url: `/pages/login` })
          }
        }
      })
    }).catch(() => {
      proxy.$modal.closeLoading()
      if (captchaEnabled.value) {
        getCode()
      }
    })
  }

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

      .register-btn {
        margin-top: 40px;
        height: 45px;
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
  .normal-login-container { position: relative; min-height: 100vh; box-sizing: border-box; overflow: hidden; padding: calc(var(--status-bar-height) + 52rpx) 52rpx calc(40rpx + env(safe-area-inset-bottom)); background: linear-gradient(155deg, #fafbff 0%, #fff 48%, #f7f5ff 100%); }
  .login-ambient { position: absolute; border-radius: 50%; filter: blur(18rpx); pointer-events: none; }
  .ambient-top { width: 480rpx; height: 480rpx; top: -260rpx; right: -230rpx; background: rgba(77,207,237,.15); }
  .ambient-bottom { width: 420rpx; height: 420rpx; bottom: -260rpx; left: -210rpx; background: rgba(157,127,245,.13); }
  .normal-login-container .logo-content { position: relative; z-index: 2; width: 100%; padding-top: 0; display: flex; flex-direction: column; align-items: center; }
  .login-logo { position: relative; width: 96rpx; height: 96rpx; border-radius: 32rpx; background: linear-gradient(145deg, #8b83f5, #4acbea); box-shadow: 0 18rpx 40rpx rgba(95,121,218,.22); transform: rotate(8deg); }
  .login-logo-core { position: absolute; width: 40rpx; height: 40rpx; left: 28rpx; top: 28rpx; border-radius: 50%; background: rgba(255,255,255,.9); }
  .normal-login-container .logo-content .title { margin: 25rpx 0 0; font-size: 35rpx; font-weight: 650; letter-spacing: 2rpx; color: #292b36; }
  .subtitle { margin-top: 8rpx; font-size: 20rpx; color: #a3a6b2; }
  .normal-login-container .login-form-content { position: relative; z-index: 2; width: 100%; max-width: 680rpx; margin: 46rpx auto 0; padding: 36rpx 34rpx 30rpx; box-sizing: border-box; border: 1px solid rgba(231,232,240,.88); border-radius: 38rpx; background: rgba(255,255,255,.84); box-shadow: 0 24rpx 70rpx rgba(61,66,102,.08); backdrop-filter: blur(16rpx); }
  .form-title { display: block; text-align: left; font-size: 32rpx; font-weight: 620; color: #30323c; }
  .form-subtitle { display: block; margin-top: 9rpx; text-align: left; font-size: 21rpx; color: #a0a2ad; }
  .normal-login-container .login-form-content .input-item { width: 100%; height: 86rpx; margin: 21rpx 0 0; border: 1px solid #ececf3; border-radius: 23rpx; background: #f8f9fc; }
  .normal-login-container .login-form-content .input-item .input { font-size: 25rpx; color: #333540; }
  .normal-login-container .login-form-content .captcha-item { position: relative; padding-right: 205rpx; box-sizing: border-box; }
  .normal-login-container .login-form-content .captcha-item .login-code { position: absolute; right: 8rpx; top: 6rpx; width: 190rpx; height: 72rpx; overflow: hidden; border-radius: 17rpx; }
  .normal-login-container .login-form-content .captcha-item .login-code-img { position: static; width: 190rpx; height: 72rpx; margin: 0; }
  .normal-login-container .login-form-content .register-btn { height: 86rpx; margin-top: 30rpx; border-radius: 25rpx; line-height: 86rpx; font-size: 27rpx; color: #fff; background: linear-gradient(135deg, #817df1, #56c9e9); box-shadow: 0 16rpx 36rpx rgba(96,119,215,.2); }
  .normal-login-container .login-form-content .register-btn::after { border: none; }
  .normal-login-container > .xieyi { position: relative; z-index: 2; margin-top: 26rpx; font-size: 23rpx; }
  @media screen and (min-width: 900px) {
    .normal-login-container { padding-top: 40px; }
    .login-logo { width: 62px; height: 62px; border-radius: 20px; }
    .login-logo-core { width: 26px; height: 26px; left: 18px; top: 18px; }
    .normal-login-container .logo-content .title { margin-top: 16px; font-size: 23px; }
    .subtitle { margin-top: 5px; font-size: 12px; }
    .normal-login-container .login-form-content { width: 430px; margin-top: 28px; padding: 24px 28px 22px; border-radius: 24px; }
    .form-title { font-size: 21px; }
    .form-subtitle { margin-top: 6px; font-size: 12px; }
    .normal-login-container .login-form-content .input-item { height: 50px; margin-top: 13px; border-radius: 15px; }
    .normal-login-container .login-form-content .register-btn { height: 50px; margin-top: 20px; border-radius: 15px; line-height: 50px; font-size: 15px; }
  }
</style>
