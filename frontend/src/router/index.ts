// createRouter：创建路由器；createWebHistory：使用正常的网址形式记录浏览历史
import { createRouter, createWebHistory } from 'vue-router'
// 创建路由器
const router = createRouter({
  // history：路由模式，
  // routes：路由列表
  history: createWebHistory(),
  routes: [
    { path: '/ai-workbench', name: 'AIWorkbench', component: () => import('../components/workbench/WorkbenchWorkspace.vue') },
    { path: '/operations', name: 'Operations', component: () => import('../components/operations/OperationsWorkspace.vue') },
    { path: '/patrol-evaluation', name: 'PatrolEvaluation', redirect: to => ({ path: '/environment', query: to.query, hash: to.hash }) },
    { path: '/environment', name: 'Environment', component: () => import('../views/Environment/index.vue') },
    { path: '/traffic', name: 'Traffic', component: () => import('../views/Traffic/index.vue') },
    { path: '/route-planning', name: 'RoutePlanning', component: () => import('../views/RoutePlanning/index.vue') },
    { path: '/positioning', name: 'Positioning', component: () => import('../views/Positioning/index.vue') },
    { path: '/airspace', name: 'Airspace', component: () => import('../views/Airspace/index.vue') },
    {
      path: '/',
      redirect: '/general'
    },
    {
      // 浏览器地址
      path: '/digital-twin',
      // 路由名称
      name: 'DigitalTwin',
      // 该地址显示的Vue组件，() => import(‘文件路径’)即访问该页面才加载——“懒加载”
      component: () => import('../views/DigitalTwin/index.vue')
    },
    {
      path: '/task-management',
      name: 'TaskManagement',
      component: () => import('../views/TaskManagement/index.vue')
    },
    {
      path: '/general',
      name: 'General',
      component: () => import('../views/General/index.vue')
    },
    {
      path: '/agent-command',
      name: 'AgentCommand',
      component: () => import('../views/AgentCommand/index.vue')
    },
    {
      path: '/logistics',
      name: 'Logistics',
      component: () => import('../views/Logistics/index.vue')
    },
    {
      path: '/emergency-process',
      name: 'EmergencyProcess',
      component: () => import('../views/EmergencyProcess/index.vue')
    },
    {
      path: '/patrol-report',
      name: 'PatrolReport',
      component: () => import('../views/PatrolReport/index.vue')
    }
  ]
})
// 导出路由器，供main.ts使用
export default router
