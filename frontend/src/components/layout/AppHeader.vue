<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useClock } from '../../composables/useClock'
import { useSystemStatus } from '../../composables/useSystemStatus'

//导航配置集中写在数组中
//以后新增导航只需要在这里改动
const navigationItems = [
    { label: '业务运营', path: '/operations' },
    { label: 'AI工作台', path: '/ai-workbench' },
    {
        label:'运行总览',
        path:'/general'
    },
    {
        label:'数字孪生',
        path:'/digital-twin'
    },
    {
        label:'Agent指挥',
        path:'/agent-command'
    },
    {
        label:'物流运输',
        path:'/logistics'
    },
    {
        label:'任务管理',
        path:'/task-management'
    },
    { label: '空域管控', path: '/airspace' },
    { label: '航线规划', path: '/route-planning' },
    { label: '多机协同', path: '/traffic' },
    { label: '环境发现', path: '/environment' },
    { label: '定位回放', path: '/positioning' },
    {
        label:'应急处理',
        path:'/emergency-process'
    },
    {
        label:'巡检报告',
        path:'/patrol-report'
    }
]

const { formattedTime,isoTime } = useClock()
const { status,statusText} = useSystemStatus()
</script>

<template>
    <header class="app-header">
    <!-- 左侧：Logo和系统名称 -->
    <div class = "brand-area">
              <!-- 临时使用SVG图标，以后可以替换成正式Logo图片 -->
      <svg
        class="brand-logo"
        viewBox="0 0 48 48"
        aria-hidden="true"
      >
        <circle cx="10" cy="10" r="5" />
        <circle cx="38" cy="10" r="5" />
        <circle cx="10" cy="38" r="5" />
        <circle cx="38" cy="38" r="5" />

        <path d="M14 13 L21 20" />
        <path d="M34 13 L27 20" />
        <path d="M14 35 L21 28" />
        <path d="M34 35 L27 28" />

        <circle cx="24" cy="24" r="6" />
      </svg>
      <div class="brand-text">
        <strong class="brand-name">SkyTwin AI</strong>
        <span class="brand-subtitle">城市低空智能管控平台</span>
      </div>
    </div>
    <!-- 中间：页面导航 -->
    <nav class="navigation" aria-label="主导航">
      <RouterLink
        v-for="item in navigationItems"
        :key="item.path"
        :to="item.path"
        class="navigation-link"
        exact-active-class="navigation-link--active"
      >
        {{ item.label }}
      </RouterLink>
    </nav>

    <!-- 右侧：运行状态 -->
    <div class="header-status">
      <!-- 当前只是模式标签，所以使用span -->
      <span
        class="simulation-badge"
        title="当前平台使用仿真数据进行演示"
      >
        仿真演示
      </span>

      <span class="status-divider" aria-hidden="true"></span>

      <time
        class="current-time"
        :datetime="isoTime"
      >
        {{ formattedTime }}
      </time>

      <div
        class="system-status"
        :class="`system-status--${status}`"
        aria-live="polite"
      >
        <span class="status-dot"></span>
        <span>{{ statusText }}</span>
      </div>
    </div>
    </header>
</template>

<style scoped>
.app-header {
  /* 顶部栏固定高度 */
  height: 68px;
  flex-shrink: 0;

  /* 分为左、中、右三列 */
  display: grid;
  grid-template-columns: minmax(260px, 500px) minmax(0, 1fr) auto;
  align-items: stretch;

  padding: 0 22px;

  background:
    linear-gradient(
      180deg,
      rgba(7, 25, 45, 0.98) 0%,
      rgba(3, 16, 31, 0.98) 100%
    );

  border-bottom: 1px solid rgba(24, 151, 220, 0.38);

  box-shadow:
    0 8px 24px rgba(0, 0, 0, 0.28),
    inset 0 -1px 10px rgba(0, 174, 255, 0.06);

  color: #dcefff;
  position: relative;
  z-index: 100;
}

/* 顶部细光线 */
.app-header::after {
  content: '';
  position: absolute;
  right: 0;
  bottom: -1px;
  left: 0;
  height: 1px;

  background: linear-gradient(
    90deg,
    transparent,
    rgba(0, 190, 255, 0.75),
    transparent
  );
}

/* 左侧品牌区域 */
.brand-area {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-logo {
  width: 40px;
  height: 40px;
  flex-shrink: 0;

  fill: none;
  stroke: #12c9ff;
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;

  filter: drop-shadow(0 0 7px rgba(18, 201, 255, 0.5));
}

.brand-text {
  min-width: 0;
  display: flex;
  align-items: baseline;
  gap: 18px;
  white-space: nowrap;
}

.brand-name {
  color: #69d5ff;
  font-size: 25px;
  font-weight: 700;
  letter-spacing: 0.5px;

  text-shadow: 0 0 12px rgba(31, 186, 255, 0.28);
}

.brand-subtitle {
  /* 明确指定中文字体，减少粗糙感 */
  font-family:
    'Microsoft YaHei UI',
    'Microsoft YaHei',
    'PingFang SC',
    sans-serif;
  color: #edf8ff;
  font-size: 20px;
  font-weight: 500;
    /* 稍微拉开中文字距 */
    letter-spacing: 0.6px;

/* 让文字看起来更干净 */
line-height: 1;

/* 比原来更接近纯白 */
color: #f4f9fd;

/* 只保留非常轻的蓝色光感 */
text-shadow: 0 0 8px rgba(74, 190, 255, 0.12);
}

/* 中间导航 */
.navigation {
  height: 100%;
  display: flex;
  align-items: stretch;
  justify-content: flex-start;
  min-width: 0;
  overflow-x: auto;
}

.navigation-link {
  position: relative;

  display: flex;
  align-items: center;
  justify-content: center;

  min-width: 104px;
  padding: 0 18px;

  color: #b8cee0;
  font-size: 15px;
  text-decoration: none;
  white-space: nowrap;

  border-right: 1px solid rgba(51, 135, 183, 0.12);

  transition:
    color 180ms ease,
    background-color 180ms ease,
    text-shadow 180ms ease;
}

.navigation-link:first-child {
  border-left: 1px solid rgba(51, 135, 183, 0.12);
}

.navigation-link:hover {
  color: #ffffff;
  background: rgba(0, 153, 255, 0.07);
}

/* 当前页面导航样式 */
.navigation-link--active {
  color: #dff7ff;
  font-weight: 600;

  background: linear-gradient(
    180deg,
    transparent 12%,
    rgba(0, 151, 255, 0.14) 100%
  );

  text-shadow: 0 0 10px rgba(51, 194, 255, 0.72);
}

/* 当前菜单底部光条 */
.navigation-link--active::after {
  content: '';
  position: absolute;
  right: 16px;
  bottom: 0;
  left: 16px;
  height: 3px;

  background: #13bfff;
  border-radius: 3px 3px 0 0;

  box-shadow:
    0 0 8px rgba(19, 191, 255, 0.9),
    0 0 18px rgba(19, 191, 255, 0.55);
}

/* 右侧区域 */
.header-status {
  justify-self: end;

  display: flex;
  align-items: center;
  gap: 14px;

  white-space: nowrap;
}

.simulation-badge {
  padding: 6px 13px;

  color: #ffc248;
  font-size: 13px;
  font-weight: 600;

  background: rgba(255, 170, 0, 0.06);
  border: 1px solid rgba(255, 183, 43, 0.75);
  border-radius: 4px;

  box-shadow: inset 0 0 9px rgba(255, 174, 0, 0.06);
}

.status-divider {
  width: 1px;
  height: 24px;
  background: rgba(129, 185, 218, 0.28);
}

.current-time {
  color: #d6e7f3;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}

/* 系统状态公共样式 */
.system-status {
  display: flex;
  align-items: center;
  gap: 7px;

  font-size: 13px;
  font-weight: 600;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;

  background: currentColor;
  box-shadow: 0 0 8px currentColor;
}

/* 检测中 */
.system-status--checking {
  color: #39c8ff;
}

/* 在线 */
.system-status--online {
  color: #25ef9a;
}

.system-status--online .status-dot {
  animation: status-pulse 1.8s infinite;
}

/* 异常 */
.system-status--warning {
  color: #ffbd3d;
}

/* 离线 */
.system-status--offline {
  color: #ff5d68;
}

@keyframes status-pulse {
  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }

  50% {
    opacity: 0.48;
    transform: scale(1.35);
  }
}

/* 屏幕较窄时隐藏平台副标题 */
@media (max-width: 1800px) {
  .app-header {
    grid-template-columns: 220px 1fr auto;
    padding: 0 16px;
  }

  /* 窄屏时，英文和中文改为上下排列 */
  .brand-text {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .brand-subtitle {
    display: block;
    font-size: 12px;
    letter-spacing: 0.3px;
  }

  .navigation-link {
    min-width: 88px;
    padding: 0 12px;
  }
}

/* 更窄时先隐藏时间，避免菜单被挤坏 */
@media (max-width: 1150px) {
  .current-time,
  .status-divider {
    display: none;
  }
}
</style>
