package com.ruoyi.skytwin;

import java.util.*;
import java.time.LocalDateTime;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import com.ruoyi.common.exception.ServiceException;

/** The business state machine owns task completion; the browser only renders it. */
@Service
public class SkyService {
    private final SkyRepository db;
    private final AirspaceService airspace;
    private final PositionService positioning;
    private final FlightRoutes routes;
    private final TrafficService traffic;
    private static final Set<String> TERMINAL=Set.of("completed","cancelled","failed");
    public SkyService(SkyRepository db,AirspaceService airspace,PositionService positioning,FlightRoutes routes,TrafficService traffic) { this.db=db; this.airspace=airspace;this.positioning=positioning;this.routes=routes;this.traffic=traffic; }
    private static String id(String prefix) { return prefix+UUID.randomUUID().toString().replace("-",""); }
    private static String s(Map<String,Object> row,String key) { return Objects.toString(row.get(key),""); }
    private static double n(Map<String,Object> row,String key) { return ((Number)row.get(key)).doubleValue(); }
    private static void require(boolean condition,String message) { if(!condition) throw new ServiceException(message,409); }
    private void audit(String id,String action,String reason,String actor) {
        db.update("INSERT INTO st_audit(entity_id,action,reason,actor) VALUES(?,?,?,?)",id,action,reason,actor);
    }
    public List<Map<String,Object>> aircraft() { return positioning.overlay(db.rows("SELECT * FROM st_aircraft WHERE deleted=0 ORDER BY created_time,id")); }
    public List<Map<String,Object>> stations() { return db.rows("SELECT * FROM st_station WHERE deleted=0 ORDER BY created_time,id"); }
    public List<Map<String,Object>> tasks() {
        return routes.attach(db.rows("SELECT t.*,a.name aircraft_name,s.name start_station_name,e.name end_station_name,s.longitude start_lon,s.latitude start_lat,e.longitude end_lon,e.latitude end_lat,er.discovery_id,er.priority response_priority FROM st_task t LEFT JOIN st_aircraft a ON a.id=t.aircraft_id JOIN st_station s ON s.id=t.start_station_id JOIN st_station e ON e.id=t.end_station_id LEFT JOIN st_env_response er ON er.task_id=t.id ORDER BY t.created_time DESC LIMIT 500"));
    }
    public List<Map<String,Object>> events() { return db.rows("SELECT e.*,d.id discovery_id,d.longitude,d.latitude FROM st_event e LEFT JOIN st_env_discovery d ON d.event_id=e.id ORDER BY e.id DESC LIMIT 500"); }
    public List<Map<String,Object>> reports() { return db.rows("SELECT * FROM st_report ORDER BY id DESC LIMIT 500"); }
    public List<Map<String,Object>> audits() { return db.rows("SELECT * FROM st_audit ORDER BY id DESC LIMIT 500"); }
    public List<Map<String,Object>> tracks(String taskId) {
        db.one("SELECT id FROM st_task WHERE id=?",taskId);
        return db.rows("SELECT * FROM st_track WHERE task_id=? ORDER BY id LIMIT 2000",taskId);
    }
    @Transactional(readOnly=true)
    public Map<String,Object> snapshot() {
        Map<String,Object> result=new LinkedHashMap<>();
        result.put("aircraft",aircraft()); result.put("stations",stations()); result.put("tasks",tasks());
        result.put("events",events()); result.put("reports",reports()); result.put("audit",audits());
        result.put("airspaceZones",airspace.zones());
        result.put("summary",Map.of("aircraft",db.count("SELECT COUNT(*) FROM st_aircraft WHERE deleted=0"),
            "executing",db.count("SELECT COUNT(*) FROM st_task WHERE status='executing'"),
            "completed",db.count("SELECT COUNT(*) FROM st_task WHERE status='completed'"),
            "openEvents",db.count("SELECT COUNT(*) FROM st_event WHERE status='open'")));
        result.put("simulation",Map.of("enabled",true,"timeScale",10,"coordinateSystem","WGS84","realFlight",false));
        return result;
    }
    @Transactional
    public String saveAircraft(String aircraftId,SkyInputs.Aircraft x,String actor) {
        require(x.type().equals("evtol") ? x.seats()>0 : x.seats()==0,"仅 eVTOL 可设置座位，且至少一个座位");
        if(aircraftId==null) {
            aircraftId=id("A-");
            db.update("INSERT INTO st_aircraft(id,name,type,model,longitude,latitude,battery,payload_capacity,seats) VALUES(?,?,?,?,?,?,?,?,?)",
                aircraftId,x.name(),x.type(),x.model(),x.longitude(),x.latitude(),x.battery(),x.payloadCapacity(),x.seats());
        } else {
            var current=db.one("SELECT * FROM st_aircraft WHERE id=? AND deleted=0 FOR UPDATE",aircraftId);
            PositionService.assertSimulationAvailable(db,aircraftId);
            require(s(current,"status").equals("idle"),"飞行器已被任务占用，不能修改资源或电量");
            db.update("UPDATE st_aircraft SET name=?,type=?,model=?,longitude=?,latitude=?,battery=?,payload_capacity=?,seats=?,altitude=0,speed=0 WHERE id=?",
                x.name(),x.type(),x.model(),x.longitude(),x.latitude(),x.battery(),x.payloadCapacity(),x.seats(),aircraftId);
        }
        audit(aircraftId,"aircraft.save","维护飞行器资源",actor); return aircraftId;
    }
    @Transactional
    public void removeAircraft(String aircraftId,String actor) {
        var a=db.one("SELECT * FROM st_aircraft WHERE id=? AND deleted=0 FOR UPDATE",aircraftId);
        PositionService.assertSimulationAvailable(db,aircraftId);
        require(s(a,"status").equals("idle"),"任务占用的飞行器不能移除");
        db.update("UPDATE st_aircraft SET deleted=1 WHERE id=?",aircraftId);
        audit(aircraftId,"aircraft.remove","移除资源，保留历史任务与轨迹",actor);
    }
    private void assertStationFree(String stationId) {
        require(db.count("SELECT COUNT(*) FROM st_task WHERE (start_station_id=? OR end_station_id=?) AND status IN('created','assigned','executing')",stationId,stationId)==0,
            "站点存在未结束任务，不能编辑或移除");
    }
    @Transactional
    public String saveStation(String stationId,SkyInputs.Station x,String actor) {
        if(stationId==null) {
            stationId=id("S-");
            db.update("INSERT INTO st_station(id,name,type,longitude,latitude,status) VALUES(?,?,?,?,?,?)",stationId,x.name(),x.type(),x.longitude(),x.latitude(),x.status());
        } else {
            db.one("SELECT id FROM st_station WHERE id=? AND deleted=0 FOR UPDATE",stationId); assertStationFree(stationId);
            db.update("UPDATE st_station SET name=?,type=?,longitude=?,latitude=?,status=? WHERE id=?",x.name(),x.type(),x.longitude(),x.latitude(),x.status(),stationId);
        }
        audit(stationId,"station.save","维护站点资源",actor); return stationId;
    }
    @Transactional
    public void removeStation(String stationId,String actor) {
        db.one("SELECT id FROM st_station WHERE id=? AND deleted=0 FOR UPDATE",stationId); assertStationFree(stationId);
        db.update("UPDATE st_station SET deleted=1 WHERE id=?",stationId); audit(stationId,"station.remove","移除站点，保留历史",actor);
    }
    private Map<String,Object> station(String id) {
        var st=db.one("SELECT * FROM st_station WHERE id=? AND deleted=0 AND status='enabled' FOR UPDATE",id);
        return st;
    }
    @Transactional
    public String createTask(SkyInputs.Task x,String actor) {
        require(!x.startStationId().equals(x.endStationId()),"起点与终点不能相同");
        // Stable locking order for operations sharing stations.
        var ids=new ArrayList<>(List.of(x.startStationId(),x.endStationId())); Collections.sort(ids);
        var first=station(ids.get(0)); var second=station(ids.get(1));
        var from=x.startStationId().equals(ids.get(0))?first:second;
        var to=x.endStationId().equals(ids.get(0))?first:second;
        if(x.type().equals("commute")) {
            require(x.passengers()>0 && s(from,"type").equals("vertiport") && s(to,"type").equals("vertiport"),"通勤任务需要乘客及两个 eVTOL 起降场");
        } else require(x.passengers()==0,"只有通勤任务可设置乘客");
        RouteEngine.Plan initial;
        try { initial=RouteEngine.build(1,new RouteEngine.Waypoint(n(from,"longitude"),n(from,"latitude")),new RouteEngine.Waypoint(n(to,"longitude"),n(to,"latitude")),List.of(),x.speed(),x.cruiseAltitude(),null); }
        catch(IllegalArgumentException ex) { throw new ServiceException(ex.getMessage(),409); }
        int duration=initial.durationSeconds();
        String taskId=id("T-");
        db.update("INSERT INTO st_task(id,title,type,start_station_id,end_station_id,payload,passengers,speed,cruise_altitude,duration_seconds,reason,created_by) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            taskId,x.title(),x.type(),x.startStationId(),x.endStationId(),x.payload(),x.passengers(),x.speed(),x.cruiseAltitude(),duration,x.reason(),actor);
        routes.store(taskId,initial,x.reason(),actor);
        audit(taskId,"task.create",x.reason(),actor); return taskId;
    }
    @Transactional
    public void taskAction(String taskId,String action,SkyInputs.Action x,String actor) {
        TrafficService.lock(db);
        var t=db.one("SELECT * FROM st_task WHERE id=? FOR UPDATE",taskId);
        String state=s(t,"status");
        if(action.equals("assign")) {
            require(state.equals("created"),"仅新建任务可以分配"); require(x.aircraftId()!=null,"请选择飞行器");
            var a=db.one("SELECT * FROM st_aircraft WHERE id=? AND deleted=0 FOR UPDATE",x.aircraftId());
            require(s(a,"status").equals("idle"),"该飞行器已被其他任务占用");
            validateDispatch(t,a);
            db.update("UPDATE st_task SET aircraft_id=?,status='assigned',reason=?,updated_time=NOW(3) WHERE id=?",x.aircraftId(),x.reason(),taskId);
            db.update("UPDATE st_aircraft SET status='assigned' WHERE id=?",x.aircraftId());
        } else if(action.equals("start")) {
            require(state.equals("assigned"),"请先分配飞行器，再执行任务");
            var a=db.one("SELECT * FROM st_aircraft WHERE id=? FOR UPDATE",t.get("aircraftId"));
            require(s(a,"status").equals("assigned"),"飞行器状态异常");
            validateDispatch(t,a);
            var launch=routes.current(taskId,true).points().get(0);
            var from=Map.<String,Object>of("longitude",launch.longitude(),"latitude",launch.latitude());
            airspace.assertAllowed(taskId,"start",actor);
            OperationsRules.assertStationLaunch(db,t);
            traffic.assertLaunch(t,actor);
            db.update("UPDATE st_task SET status='executing',reason=?,updated_time=NOW(3) WHERE id=?",x.reason(),taskId);
            db.update("UPDATE st_traffic_slot SET status='running',updated_time=NOW(3) WHERE task_id=? AND status='reserved'",taskId);
            // Simulation launch position, never a real flight command.
            db.update("UPDATE st_aircraft SET status='flying',longitude=?,latitude=?,altitude=0,speed=? WHERE id=?",from.get("longitude"),from.get("latitude"),t.get("speed"),t.get("aircraftId"));
            track(t,a,from,0,0,n(t,"speed"));
        } else if(action.equals("cancel") || action.equals("fail")) {
            require(!TERMINAL.contains(state),"任务已结束，不能重复终止");
            finish(t,action.equals("cancel")?"cancelled":"failed",x.reason(),actor);
        } else throw new ServiceException("不支持的任务操作",400);
        audit(taskId,"task."+action,x.reason(),actor);
    }

    private void validateDispatch(Map<String,Object> task, Map<String,Object> aircraft) {
        PositionService.assertSimulationAvailable(db,s(aircraft,"id"));
        // Deadline is immutable. Read without locking the order after the task,
        // avoiding the reverse of the order -> task locking order used above.
        var orders="logistics".equals(s(task,"type"))?db.rows("SELECT deadline_at FROM st_logistics_order WHERE task_id=?",task.get("id")):List.<Map<String,Object>>of();
        var deadline=orders.isEmpty()?null:LocalDateTime.parse(s(orders.get(0),"deadlineAt"));
        var reasons=DispatchOptimizer.constraintReasons(s(task,"type"),n(task,"durationSeconds"),n(task,"payload"),
            (int)n(task,"passengers"),deadline,DispatchOptimizer.vehicle(aircraft),LocalDateTime.now());
        require(reasons.isEmpty(),String.join("；",reasons));
    }
    private void finish(Map<String,Object> t,String status,String reason,String actor) {
        db.update("UPDATE st_traffic_slot SET status=?,message=?,updated_time=NOW(3) WHERE task_id=? AND status IN('reserved','running')",status,reason,t.get("id"));
        db.update("UPDATE st_task SET status=?,progress=IF(?='completed',100,progress),reason=?,updated_time=NOW(3) WHERE id=?",status,status,reason,t.get("id"));
        if(t.get("aircraftId")!=null) db.update("UPDATE st_aircraft SET status='idle',speed=0,altitude=0 WHERE id=?",t.get("aircraftId"));
        if(status.equals("failed")) db.update("INSERT INTO st_event(task_id,aircraft_id,severity,title) VALUES(?,?,'high',?)",t.get("id"),t.get("aircraftId"),reason);
        String content="仿真任务摘要（系统生成，非 AI 影像分析）\n任务："+s(t,"title")+"\n类型："+s(t,"type")+"\n结果："+status+"\n原因："+reason+"\n飞行器："+s(t,"aircraftId")+"\n轨迹点："+db.count("SELECT COUNT(*) FROM st_track WHERE task_id=?",t.get("id"))+"\n所有位置和状态来自本地仿真，不代表真实飞行。";
        db.update("INSERT INTO st_report(task_id,title,content,created_by) VALUES(?,?,?,?)",t.get("id"),s(t,"title")+" · 任务报告",content,actor);
    }
    @Transactional
    public void resolveEvent(long eventId,String reason,String actor) {
        TrafficService.lock(db);
        require(db.count("SELECT COUNT(*) FROM st_env_discovery WHERE event_id=?",eventId)==0,"环境事件须在环境发现闭环完成侦察和处置后证据，不能通过通用处置接口直接结案");
        var e=db.one("SELECT * FROM st_event WHERE id=? FOR UPDATE",eventId);
        require(s(e,"status").equals("open"),"事件已处置");
        db.update("UPDATE st_event SET status='resolved',resolution=?,resolved_by=?,resolved_time=NOW(3) WHERE id=?",reason,actor,eventId);
        audit("event-"+eventId,"event.resolve",reason,actor);
    }
    public List<Map<String,Object>> runningTasks() { return db.rows("SELECT id FROM st_task WHERE status='executing' ORDER BY id"); }
    // Only advanceSimulation may tick: never move one aircraft independently of the shared clock.
    private void tickInternal(String taskId) {
        var t=db.one("SELECT * FROM st_task WHERE id=? FOR UPDATE",taskId);
        if(!s(t,"status").equals("executing")) return;
        var a=db.one("SELECT * FROM st_aircraft WHERE id=? FOR UPDATE",t.get("aircraftId"));
        if(n(a,"battery")<=15) { finish(t,"failed","仿真电量低于安全阈值，任务终止","simulator"); audit(taskId,"task.fail","电量保护","simulator"); return; }
        var route=routes.current(taskId,true);
        double previous=n(t,"elapsedSeconds"),elapsed=Math.min(route.durationSeconds(),previous+1);
        double p=elapsed/route.durationSeconds();
        var position=RouteEngine.at(route.points(),elapsed);
        double lon=position.longitude(),lat=position.latitude(),altitude=position.altitude();
        double battery=Math.max(0,n(a,"battery")-0.08);
        double speed=(p>=1 || p<=0.1 || p>=0.9)?0:n(t,"speed");
        db.update("UPDATE st_aircraft SET longitude=?,latitude=?,altitude=?,battery=?,speed=? WHERE id=?",lon,lat,altitude,battery,speed,a.get("id"));
        db.update("UPDATE st_task SET progress=?,elapsed_seconds=elapsed_seconds+1,updated_time=NOW(3) WHERE id=?",p*100,taskId);
        // Preserve fractional-time corners, otherwise a polyline of 1Hz samples cuts across turns.
        for(var corner:route.points()) if(corner.offsetSeconds()>previous && corner.offsetSeconds()<elapsed) {
            double progress=corner.offsetSeconds()/route.durationSeconds()*100;
            double atBattery=Math.max(0,n(a,"battery")-(corner.offsetSeconds()-previous)*.08);
            track(t,Map.of("battery",atBattery),Map.of("longitude",corner.longitude(),"latitude",corner.latitude()),progress,corner.altitude(),n(t,"speed"));
        }
        track(t,Map.of("battery",battery),Map.of("longitude",lon,"latitude",lat),p*100,altitude,speed);
        if(n(a,"battery")>30 && battery<=30) {
            db.update("INSERT INTO st_event(task_id,aircraft_id,severity,title) VALUES(?,?,'medium','仿真飞行器电量低于 30%')",taskId,a.get("id"));
            audit(taskId,"event.low-battery","生成低电量告警","simulator");
        }
        if(p>=1) { finish(t,"completed","仿真飞行器抵达终点并降落","simulator"); audit(taskId,"task.complete","服务端确认降落，完成任务","simulator"); }
    }
    /** All aircraft and clock advance atomically. Restart pauses both, never wall-clock catch-up. */
    @Transactional
    public void advanceSimulation() {
        TrafficService.lock(db);
        for(var row:runningTasks()) tickInternal(s(row,"id"));
        db.update("UPDATE st_traffic_clock SET tick=tick+1 WHERE id=1");
        long clock=traffic.tick();
        for(var slot:db.rows("SELECT * FROM st_traffic_slot WHERE status='reserved' AND departure_tick<=? ORDER BY departure_tick,task_id FOR UPDATE",clock)) {
            String taskId=s(slot,"taskId");var t=db.one("SELECT * FROM st_task WHERE id=? FOR UPDATE",taskId);
            var a=db.one("SELECT * FROM st_aircraft WHERE id=? FOR UPDATE",slot.get("aircraftId"));
            var problems=new ArrayList<String>();
            if(!s(t,"aircraftId").equals(s(slot,"aircraftId")) || routes.current(taskId,true).revision()!=(int)n(slot,"routeRevision")) problems.add("预约航线或飞行器已变化");
            problems.addAll(traffic.constraints(t,a,LocalDateTime.now()));
            var candidate=new TrafficEngine.Flight(taskId,s(t,"title"),s(t,"aircraftId"),clock,routes.current(taskId,true).points());
            if(!TrafficEngine.conflicts(candidate,traffic.obstacles(clock),clock).isEmpty()) problems.add("到点复核发现多机时空冲突");
            if(!problems.isEmpty()) {
                String message=String.join("；",problems);
                db.update("UPDATE st_traffic_slot SET status='blocked',message=?,updated_time=NOW(3) WHERE task_id=?",message,taskId);
                audit(taskId,"traffic.blocked",message,"simulator");
            } else taskAction(taskId,"start",new SkyInputs.Action(null,"按已确认错峰预约起飞"),"simulator");
        }
    }
    private void track(Map<String,Object> t,Map<String,Object> a,Map<String,Object> pos,double progress,double altitude,double speed) {
        db.update("INSERT INTO st_track(task_id,aircraft_id,longitude,latitude,altitude,battery,speed,progress) VALUES(?,?,?,?,?,?,?,?)",t.get("id"),t.get("aircraftId"),pos.get("longitude"),pos.get("latitude"),altitude,a.get("battery"),speed,progress);
    }
}
