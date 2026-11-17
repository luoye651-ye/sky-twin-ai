// 创建Vue应用的导入，有大括号则名称必须和导出的名称一致
import { createApp } from 'vue'
// 创建数据共享的状态管理器
import { createPinia } from 'pinia'
// 导入UI组件库以及样式
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
// 导入根组件，App是自定义的名字
import App from './App.vue'
// 导入路由
import router from './router'
import './style.css'
// 创建应用App.vue到app中
const app = createApp(App)
// 用use安装插件到app中
app.use(createPinia())
app.use(router)
app.use(ElementPlus)
//mount挂载应用，把Vue应用放在id为app的元素中
app.mount('#app')
