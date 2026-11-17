// 导入工具
import { defineStore } from 'pinia'
import { ref } from 'vue'
//导入前后端匹配的接口
import { dispatchTask, fetchDroneList } from '../api/drone'
import type { Drone, Mission } from '../types/drone'
// 创建仓库，useDroneStore是其他组件使用仓库的函数
export const useDroneStore = defineStore('drone', () => {
  // 定义共享数据
  // drones：无人机数组；activeMission：当前任务；loading：是否正在加载
  const drones = ref<Drone[]>([])
  const activeMission = ref<Mission | null>(null)
  const loading = ref(false)

  async function loadDrones() {
    loading.value = true
    try {
      drones.value = await fetchDroneList()
    } finally {
      loading.value = false
    }
  }
// 下发任务
  async function sendTask(droneId: string, area: string) {
    const mission = await dispatchTask(droneId, area)
    // 保存当前任务
    activeMission.value = mission
    const drone = drones.value.find((d) => d.id === droneId)
    // 若找到了无人机，则把状态改成飞行中
    if (drone) {
      drone.status = 'flying'
    }
    return mission
  }
// 公开数据和方法，这里返回的内容，其他组件可以使用
  return { drones, activeMission, loading, loadDrones, sendTask }
})
