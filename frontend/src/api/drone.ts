import axios from 'axios'
// Legacy FastAPI demo. Active business pages use api/sky.ts and the Java service.
import type { Drone, Mission } from '../types/drone'

const http = axios.create({
  // 创建一个专用请求对象，所有接口地址自动加上/api(公共地址)，http.get('drone/list')实际请求/api/drone/list
  baseURL: '/api'
})
// export：允许其他文件导入这个函数
// 获取无人机列表
export function fetchDroneList() {
  return http.get<Drone[]>('/drone/list').then((res) => res.data)
}
// 下发巡检任务
export function dispatchTask(droneId: string, area: string) {
  return http
    .post<Mission>('/drone/task', { drone_id: droneId, area })
    .then((res) => res.data)
}
