<script setup lang="ts">
withDefaults(
  defineProps<{
    title: string
    extra?: string
  }>(),
  {
    extra: ''
  }
)
</script>

<template>
  <section class="dashboard-panel">
    <header class="panel-header">
      <div class="panel-title-area">
        <!-- 后续可以向这里传入图标 -->
        <slot name="icon">
          <span class="default-icon"></span>
        </slot>

        <h2 class="panel-title">
          {{ title }}
        </h2>
      </div>

      <span v-if="extra" class="panel-extra">
        {{ extra }}
      </span>
    </header>

    <div class="panel-body">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.dashboard-panel {
  min-width: 0;
  min-height: 0;

  display: flex;
  flex-direction: column;

  position: relative;
  overflow: hidden;

  background:
    linear-gradient(
      180deg,
      rgba(7, 31, 52, 0.96),
      rgba(3, 21, 38, 0.96)
    );

  border: 1px solid rgba(34, 174, 237, 0.55);
  border-radius: 4px;

  box-shadow:
    inset 0 0 22px rgba(0, 145, 220, 0.06),
    0 0 12px rgba(0, 0, 0, 0.22);
}

/* 左上角发光装饰 */
.dashboard-panel::before {
  content: '';
  position: absolute;
  top: -1px;
  left: -1px;

  width: 42px;
  height: 3px;

  background: #4bd8ff;
  box-shadow: 0 0 8px rgba(75, 216, 255, 0.8);
}

/* 右下角发光装饰 */
.dashboard-panel::after {
  content: '';
  position: absolute;
  right: -1px;
  bottom: -1px;

  width: 42px;
  height: 3px;

  background: #4bd8ff;
  box-shadow: 0 0 8px rgba(75, 216, 255, 0.8);
}

.panel-header {
  height: 44px;
  flex-shrink: 0;

  display: flex;
  align-items: center;
  justify-content: space-between;

  padding: 0 14px;

  border-bottom: 1px solid rgba(70, 165, 210, 0.22);

  background: linear-gradient(
    90deg,
    rgba(16, 80, 116, 0.22),
    transparent
  );
}

.panel-title-area {
  display: flex;
  align-items: center;
  gap: 9px;
}

.default-icon {
  width: 9px;
  height: 9px;

  background: #48d7ff;
  border-radius: 2px;

  box-shadow: 0 0 8px rgba(72, 215, 255, 0.85);
}

.panel-title {
  margin: 0;

  color: #e9f7ff;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.panel-extra {
  color: #9fc2d7;
  font-size: 13px;
}

.panel-body {
  flex: 1;
  min-width: 0;
  min-height: 0;

  padding: 12px;
  overflow: hidden;
}
</style>