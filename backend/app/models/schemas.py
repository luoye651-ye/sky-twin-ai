# 定义一组固定选项
from enum import Enum

from pydantic import BaseModel, Field

# 无人机的状态
class DroneStatus(str, Enum):
    # 闲置
    idle = "idle"
    # 飞行中
    flying = "flying"
    # 返航ing
    returning = "returning"

# 无人机的位置信息
class Location(BaseModel):
    # 纬度
    lat: float
    # 经度
    lng: float
    # 高度
    alt: float = 0

# 无人机信息
class Drone(BaseModel):
    # 无人机id号
    id: str
    # 无人机名称
    name: str
    # 无人机位置
    location: Location
    # 无人机状态，必须是DroneStatu的一个值
    status: DroneStatus

# 下发任务的请求
class TaskRequest(BaseModel):
    # 无人机id
    drone_id: str
    # 该无人机所需要巡视的区域
    area: str = Field(description="巡检区域名称，如 'A区域'")

# 任务结果
class Mission(BaseModel):
    # 任务id
    mission_id: str
    # 无人机id
    drone_id: str
    # 飞行路线
    route: list[Location]
    # 任务状态
    status: str = "in_progress"
