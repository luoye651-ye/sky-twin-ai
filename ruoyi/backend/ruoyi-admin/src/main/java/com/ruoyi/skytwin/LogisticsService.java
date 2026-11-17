// 处理业务并保存数据
package com.ruoyi.skytwin;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.UUID;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.ruoyi.common.exception.ServiceException;
// 查询方法
import java.util.List;
import java.util.Map;

// 标记为业务服务，由Spring创建和管理这个对象
@Service
public class LogisticsService{
    private static final String ORDER_SELECT = """
        SELECT o.*, t.status AS task_status, t.progress, t.aircraft_id,
          t.start_station_id, t.end_station_id, t.duration_seconds,
          t.elapsed_seconds, t.updated_time AS task_updated_time,
          t.reason AS task_reason, t.cruise_altitude, t.speed AS planned_speed,
          a.name AS aircraft_name, a.battery AS aircraft_battery,
          a.longitude AS aircraft_longitude, a.latitude AS aircraft_latitude,
          a.altitude AS aircraft_altitude,
          s.name AS start_station_name, e.name AS end_station_name,
          NOW(3) AS server_time
        FROM st_logistics_order o
        JOIN st_task t ON t.id=o.task_id
        JOIN st_station s ON s.id=t.start_station_id
        JOIN st_station e ON e.id=t.end_station_id
        LEFT JOIN st_aircraft a ON a.id=t.aircraft_id
        """;
    // 复用项目已有的数据库工具和任务服务
    private final SkyRepository db;
    private final SkyService sky;

    //Spring 会通过构造函数传入这两个对象。
    public LogisticsService(SkyRepository db,SkyService sky){
        this.db = db;
        this.sky = sky;
    }

    /*
        创建订单。
        x:经过输入校验的订单信息
        actor:当前登录人的用户名
        本方法及其调用的任务创建操作处于同一事务
        发生运行异常时，一起回滚。
    */
   @Transactional
   public String create(LogisticsInputs.Create x,String actor){
    // 1.检查两个字段之间的业务关系
    if(x.startStationId().equals(x.endStationId())){
        throw new ServiceException("起点与终点不能相同",409);
    }
    // 2.生成订单编号，O-后面跟一串唯一标识
    String orderId =
        "O-" + UUID.randomUUID().toString().replace("-","");
   // 配送截止时间 = 当前服务端时间 + 用户填写的分钟数
   LocalDateTime deadline = LocalDateTime.now().plusMinutes(x.deadlineMinutes());
    /*
        * 3. 创建关联的物流任务。
        * 复用已有方法，它会检查站点是否存在、是否启用、
        * 起终点是否不同，以及航程范围是否符合要求。
        *
        * 创建后任务只是“待分配”，不会立即起飞。
    */
        String taskId = sky.createTask(new SkyInputs.Task(
        "配送：" + x.cargoName(), // 任务名称
        "logistics",             // 任务类型：物流配送
        x.startStationId(),      // 起点编号
        x.endStationId(),        // 终点编号
        x.weight(),              // 货物重量作为任务载荷
        0,                       // 配送任务没有乘客
        10.0,                    // 仿真速度：10 m/s
        60.0,                    // 仿真巡航高度：60 m
        x.reason()               // 创建原因
    ), actor);

    /*
    * 4. 保存订单。
    * SQL 中的六个 ?，按顺序对应后面的六个参数。
    * task_id 将订单与刚创建的任务关联起来。
    */
    db.update("""
        INSERT INTO st_logistics_order
          (id, cargo_name, weight, deadline_at, task_id, created_by)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        orderId,
        x.cargoName(),
        x.weight(),
        Timestamp.valueOf(deadline),
        taskId,
        actor
    );
    // 5.保存业务操作记录，谁因什么创建了这笔订单。
    db.update("""
        INSERT INTO st_audit
          (entity_id, action, reason, actor)
        VALUES (?, ?, ?, ?)
        """,
        orderId,
        "order.create",
        x.reason(),
        actor
    );
    // 6.返回订单编号，供调用者查询和后续操作
        return orderId;
    }
    // 查询最近200条订单，同时读取关联任务和站点名称
    public List<Map<String,Object>> list(){
        return db.rows(ORDER_SELECT + " ORDER BY o.created_time DESC,o.id DESC LIMIT 200");
    }

    @Transactional(readOnly=true)
    public Map<String,Object> detail(String orderId) {
        var order = db.one(ORDER_SELECT + " WHERE o.id=?", orderId);
        order.put("audit", db.rows("""
            SELECT id,entity_id,action,reason,actor,created_time
            FROM st_audit WHERE entity_id IN (?,?) ORDER BY id DESC LIMIT 200
            """, orderId, order.get("taskId")));
        return order;
    }

    public List<Map<String,Object>> tracks(String orderId) {
        var order = db.one("SELECT task_id FROM st_logistics_order WHERE id=?", orderId);
        return sky.tracks(order.get("taskId").toString());
    }

    // Orders and the task workbench delegate to the same task state machine.
    @Transactional
    public void action(String orderId, String action, SkyInputs.Action x, String actor) {
        if (!List.of("assign", "start", "cancel").contains(action)) {
            throw new ServiceException("不支持的配送操作", 400);
        }
        var order = db.one("SELECT * FROM st_logistics_order WHERE id=? FOR UPDATE", orderId);
        if (!"created".equals(order.get("status"))) {
            throw new ServiceException("已送达订单不能再次调度或取消", 409);
        }
        sky.taskAction(order.get("taskId").toString(), action, x, actor);
    }
    @Transactional
public void deliver(
    String orderId,
    LogisticsInputs.Deliver x,
    String actor
) {
    // 1. 查询并锁住订单，防止两个请求同时确认。
    var order = db.one("""
        SELECT * FROM st_logistics_order
        WHERE id=? FOR UPDATE
        """, orderId);

    // 2. 只有尚未确认送达的订单可以操作。
    if (!"created".equals(order.get("status"))) {
        throw new ServiceException("订单已确认送达，不能重复确认", 409);
    }

    // 3. 从数据库中的关联关系找到任务，不相信前端自报状态。
    var task = db.one("""
        SELECT * FROM st_task
        WHERE id=? FOR UPDATE
        """, order.get("taskId"));

    if (!"completed".equals(task.get("status"))) {
        throw new ServiceException("飞行任务尚未完成，不能确认送达", 409);
    }

    // 4. 更新订单，确认时间使用数据库时间。
    db.update("""
        UPDATE st_logistics_order
        SET status='delivered',
            delivered_by=?,
            delivered_at=NOW(3)
        WHERE id=?
        """, actor, orderId);

    // 5. 同时记录谁因什么确认了送达。
    db.update("""
        INSERT INTO st_audit
          (entity_id, action, reason, actor)
        VALUES (?, ?, ?, ?)
        """, orderId, "order.deliver", x.reason().trim(), actor);
}
}
