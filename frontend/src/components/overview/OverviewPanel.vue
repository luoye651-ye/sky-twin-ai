<script setup lang="ts">
defineProps<{ title: string; subtitle: string; link: string; index: string }>()
</script>
<template>
  <section class="overview-panel" :aria-label="title" data-overview-panel>
    <header class="panel-heading">
      <div><span class="panel-index">{{ index }}</span><h2>{{ title }}</h2></div>
      <RouterLink :to="link" :aria-label="`查看${title}详情`">详情 ↗</RouterLink>
    </header>
    <div class="panel-content"><slot /></div>
    <p class="panel-caption">{{ subtitle }}</p>
  </section>
</template>
<style scoped>
.overview-panel { position:relative; min-width:0; min-height:0; display:flex; flex-direction:column; overflow:hidden; border:1px solid #2371a580; background:linear-gradient(145deg,#071d35f0,#061222f2); box-shadow:inset 0 0 28px #0a5c9820,0 7px 22px #0002; border-radius:3px 14px 3px 3px; }
.overview-panel::before { content:''; position:absolute; left:0; top:0; width:34%; height:2px; background:linear-gradient(90deg,#35d9ff,transparent); box-shadow:0 0 12px #37d9ff88; }
.overview-panel::after { content:''; position:absolute; width:16px; height:16px; right:0; bottom:0; border-right:2px solid #47d9ff; border-bottom:2px solid #47d9ff; pointer-events:none; }
.panel-heading { display:flex; justify-content:space-between; align-items:center; gap:8px; min-height:38px; padding:0 12px; border-bottom:1px solid #2e78ac35; background:linear-gradient(90deg,#15488466,transparent); }
.panel-heading>div { display:flex; gap:8px; align-items:center; min-width:0; }.panel-heading h2 { margin:0; color:#dcefff; font-size:14px; letter-spacing:1px; }.panel-index { color:#48c7ff; font:10px monospace; }.panel-heading a { font-size:11px; color:#80b6d4; text-decoration:none; white-space:nowrap; }.panel-heading a:hover { color:#51e2ff; }
.panel-content { flex:1; min-height:0; padding:10px 12px 4px; overflow:auto; scrollbar-width:thin; scrollbar-color:#235b7b transparent; }.panel-caption { margin:0; padding:5px 12px 8px; color:#7b9bb7; font-size:10px; line-height:1.4; }
</style>
