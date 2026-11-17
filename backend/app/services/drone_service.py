# 生成不重复的任务编号
import uuid
# 导入schemas.py中定义的数据类型
from app.models.schemas import Drone, DroneStatus, Location, Mission

# 模拟无人机数据库
_drones: dict[str, Drone] = {
    "D-01": Drone(
        id="D-01",
        name="D-01",
        location=Location(lat=5, lng=-10, alt=8),
        status=DroneStatus.idle,
    ),
    "D-02": Drone(
        id="D-02",
        name="D-02",
        location=Location(lat=-8, lng=8, alt=6),
        status=DroneStatus.idle,
    ),
    "D-03": Drone(
        id="D-03",
        name="D-03",
        location=Location(lat=15, lng=15, alt=10),
        status=DroneStatus.idle,
    ),
}

# 模拟任务数据库，创建空字典，保存生成的巡检任务
_missions: dict[str, Mission] = {}

#  查询所有无人机
def list_drones() -> list[Drone]:
    return list(_drones.values())

# 根据编号查询无人机
def get_drone(drone_id: str) -> Drone | None:
    return _drones.get(drone_id)

# 下发巡检任务
def dispatch_mission(drone_id: str, area: str) -> Mission:
    drone = _drones.get(drone_id)
    if drone is None:
        raise ValueError(f"未知无人机: {drone_id}")


# 生成飞行路线
    start = drone.location
    # Phase 1 用一个简单矩形巡检环线代替真实航线规划算法，
    # Phase 3 会替换为 MCP drone_tool 里真正的航线规划逻辑。
    route = [
        start,
        Location(lat=start.lat + 10, lng=start.lng, alt=start.alt + 2),
        Location(lat=start.lat + 10, lng=start.lng + 10, alt=start.alt + 2),
        Location(lat=start.lat, lng=start.lng + 10, alt=start.alt + 2),
        Location(lat=start.lat, lng=start.lng, alt=start.alt),
    ]
# 修改无人机的状态为飞行ing
    drone.status = DroneStatus.flying
# 创建并保存任务
    mission = Mission(
        # 随机任务编号
        mission_id=f"M-{uuid.uuid4().hex[:8]}",
        #  执行任务的无人机id
        drone_id=drone_id,
        #  飞行路线
        route=route,
        #  任务状态为进行中
        status="in_progress",
    )
    _missions[mission.mission_id] = mission
    return mission
