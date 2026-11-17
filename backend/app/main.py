# 导入FastAPI：创建后端应用；CORSMiddleware：处理浏览器的跨域请求
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# 导入无人机路由
from app.api import drone
# 创建应用实例“app”
app = FastAPI(title="SkyTwin AI Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    # 允许哪些前端地址访问
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    # 允许携带身份信息（比如Cookie）
    allow_credentials=True,
    # 允许GET、POST等所有请求方式
    allow_methods=["*"],
    # 允许所有请求头（包括登录令牌、Cookie、来自哪个网站等）
    allow_headers=["*"],
)
# 挂载无人机路由，把drone.py中的接口添加到整个应用中，使得能够用GET /api/drone/list之类的请求
app.include_router(drone.router)

# 挂载并定义的简单接口，用来判断整个后端是否在正常运行（相当于console.log。。。）
@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
