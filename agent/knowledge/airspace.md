# SkyTwin空域安全规则

## 禁飞区命中条件

项目禁飞区类型为no_fly，当前按经纬度矩形、最低/最高高度和生效时间描述。服务端对航线路段连续检测，不是只检查航点；当启用区域的水平范围、禁飞高度范围和有效时段与航段相交，就产生违规记录。空间边界包含在范围内；规则生效时间为[开始时间,结束时间)，即包含开始、不包含结束。未启用区域不参与检查。这是项目仿真几何规则，不是政府公布的官方空域数据。

实现依据：ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/AirspaceEngine.java：checkPath。

## 限高区与恰好等于限高

限高区类型为height_limit，高度下限必须配置为0。只有航段在区域及生效时段内严格高于最高允许高度才算违规；恰好等于限高允许通过，数值比较使用微小容差。不能把项目配置的最高高度当作全国统一法定限高，也不能从这份文档推断某架飞机当前可以起飞。

实现依据：ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/AirspaceEngine.java：checkPath；AirspaceService.java：save。

## 起飞拦截与人工校验

执行任务前，Java在任务状态和资源检查后调用airspace.assertAllowed，再调用traffic.assertLaunch，通过后才将任务改为executing。命中禁飞或限高规则会拒绝启动，不能靠Agent建议或前端动画绕过。人工空域校验接口会保存检查结果；预计起飞时间允许在当前时间附近（5秒容差）到未来30天内。人工校验只是当时的检查，实际起飞仍重新读取当前规则执行安全检查。

实现依据：ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/SkyService.java：taskAction；AirspaceService.java：validate、assertAllowed。

## 区域配置约束和规则版本

区域坐标与高度必须为有限数；西经度小于东经度，南纬度小于北纬度；单区域经纬跨度各不超过2度。最低高度不能大于最高高度；如果同时设置开始和结束时间，结束必须晚于开始。第一版最多配置500个区域。保存规则会增加策略revision版本，并写审计。知识库不缓存当前禁飞区清单；查询具体当前区域或某条任务是否获准，必须使用相应业务接口，当前Agent尚未提供这些查询工具。

实现依据：ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/AirspaceService.java：save、revision、validate。
