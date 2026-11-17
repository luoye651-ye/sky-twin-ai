# APIRouter：创建一组API路由；HTTPException：向前端返回HTTP数据
from fastapi import APIRouter, HTTPException
# 从schemas.py中导入数据格式
from app.models.schemas import Drone, Mission, TaskRequest
# 导入drone_service.py的业务功能
from app.services import drone_service
# 创建路由器，prefix：接口的开头；tags：接口都归类到drone分组中
router = APIRouter(prefix="/api/drone", tags=["drone"])

# 获取无人机列表
@router.get("/list", response_model=list[Drone])
def get_drone_list() -> list[Drone]:
    return drone_service.list_drones()

# 创建巡检任务，前端传入符合TaskRequest格式的数据
@router.post("/task", response_model=Mission)
def create_task(payload: TaskRequest) -> Mission:
    try:
        # 调用drone_service中的巡检任务业务逻辑
        return drone_service.dispatch_mission(payload.drone_id, payload.area)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
