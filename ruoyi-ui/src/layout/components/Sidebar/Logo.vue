<template>
  <div class="sidebar-logo-container" :class="{ 'collapse': collapse }">
    <transition name="sidebarLogoFade">
      <router-link v-if="collapse" key="collapse" class="sidebar-logo-link" to="/">
        <span class="sidebar-logo"><i></i></span>
      </router-link>
      <router-link v-else key="expand" class="sidebar-logo-link" to="/">
        <span class="sidebar-logo"><i></i></span>
        <span class="sidebar-copy">
          <strong class="sidebar-title">天猫智家</strong>
          <small>TMALL SMART HOME</small>
        </span>
      </router-link>
    </transition>
  </div>
</template>

<script setup>
import useSettingsStore from '@/store/modules/settings'
import variables from '@/assets/styles/variables.module.scss'

defineProps({
  collapse: {
    type: Boolean,
    required: true
  }
})

const settingsStore = useSettingsStore()
const sideTheme = computed(() => settingsStore.sideTheme)

// 获取Logo背景色
const getLogoBackground = computed(() => {
  if (settingsStore.isDark) {
    return 'var(--sidebar-bg)'
  }
  if (settingsStore.navType == 3) {
    return variables.menuLightBg
  }
  return sideTheme.value === 'theme-dark' ? variables.menuBg : variables.menuLightBg
})

// 获取Logo文字颜色
const getLogoTextColor = computed(() => {
  if (settingsStore.isDark) {
    return 'var(--sidebar-logo-text)'
  }
  if (settingsStore.navType == 3) {
    return variables.menuLightText
  }
  return sideTheme.value === 'theme-dark' ? '#fff' : variables.menuLightText
})
</script>

<style lang="scss" scoped>
.sidebarLogoFade-enter-active {
  transition: opacity 1.5s;
}

.sidebarLogoFade-enter,
.sidebarLogoFade-leave-to {
  opacity: 0;
}

.sidebar-logo-container {
  position: relative;
  height: 68px;
  box-sizing: border-box;
  background: v-bind(getLogoBackground);
  overflow: hidden;

  & .sidebar-logo-link {
    // sidebar.scss 中的通用 a 标签规则优先级更高，必须在品牌组件内明确覆盖。
    display: flex !important;
    flex-direction: row;
    align-items: center !important;
    gap: 10px;
    height: 100%;
    width: 100%;
    padding: 0 14px;
    box-sizing: border-box;
    overflow: hidden;
    text-decoration: none;

    & .sidebar-logo {
      display: inline-grid;
      place-items: center;
      flex: 0 0 38px;
      width: 38px;
      height: 38px;
      border: 1px solid rgba(255, 255, 255, .13);
      border-radius: 13px 17px 13px 16px;
      background:
        radial-gradient(circle at 67% 68%, rgba(87, 219, 242, .94), transparent 42%),
        linear-gradient(145deg, #858af6 4%, #629eea 55%, #52cce8 100%);
      box-shadow: 0 7px 18px rgba(79, 127, 221, .28);
      transform: rotate(5deg);

      i {
        width: 17px;
        height: 17px;
        background: rgba(255, 255, 255, .92);
        border-radius: 50%;
        box-shadow: 0 0 14px rgba(255, 255, 255, .55);
      }
    }

    & .sidebar-copy {
      display: flex;
      flex: 1 1 auto;
      min-width: 0;
      overflow: hidden;
      flex-direction: column;
      align-items: flex-start;
      justify-content: center;
      line-height: 1;
    }

    & .sidebar-title {
      color: v-bind(getLogoTextColor);
      font-weight: 700;
      line-height: 1.2;
      font-size: 17px;
      letter-spacing: .3px;
      font-family: Avenir, Helvetica Neue, Arial, Helvetica, sans-serif;
      white-space: nowrap;
    }

    & small {
      display: block;
      max-width: 100%;
      margin-top: 4px;
      overflow: hidden;
      color: #9ba6bd;
      font-size: 7.5px;
      line-height: 1.2;
      letter-spacing: .45px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  &.collapse {
    .sidebar-logo-link {
      justify-content: center !important;
      padding: 0;
    }

    .sidebar-logo {
      flex: 0 0 36px;
      width: 36px;
      height: 36px;
    }
  }
}
</style>
