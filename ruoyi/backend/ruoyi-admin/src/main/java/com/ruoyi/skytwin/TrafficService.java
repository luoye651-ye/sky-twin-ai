package com.ruoyi.skytwin;

import java.util.*;
import java.time.LocalDateTime;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.common.exception.ServiceException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** One Java/DB authority for manual starts, persisted reservations and simulation time. */
@Service
public class TrafficService {
    private final SkyRepository db;private final FlightRoutes routes;private final AirspaceService airspace;
    private final TrafficRecords records;private final ObjectMapper mapper;
    public TrafficService(SkyRepository db,FlightRoutes routes,AirspaceService airspace,TrafficRecords records,ObjectMapper mapper) {
        this.db=db;this.routes=routes;this.airspace=airspace;this.records=records;this.mapper=mapper;
    }
    public static void lock(SkyRepository db) { db.one("SELECT tick FROM st_traffic_clock WHERE id=1 FOR UPDATE"); }
    public long tick() { return ((Number)db.one("SELECT tick FROM st_traffic_clock WHERE id=1 FOR SHARE").get("tick")).longValue(); }
    private static String s(Map<String,Object> r,String k) { return Objects.toString(r.get(k),""); }
    private static void require(boolean ok,String message) { if(!ok) throw new ServiceException(message,409); }
    private String json(Object value) {
        try { return mapper.writeValueAsString(value); } catch(Exception e) { throw new IllegalStateException("协同记录序列化失败",e); }
    }
    private <T> T parse(String value,Class<T> type) {
        try { return mapper.readValue(value,type); } catch(Exception e) { throw new IllegalStateException("协同记录读取失败",e); }
    }
    public record Slot(String taskId,String title,String aircraftId,int routeRevision,int durationSeconds,
        int delaySeconds,long departureTick,boolean allowed,List<TrafficEngine.Conflict> conflicts,List<String> problems) {}
    public record Proposal(long clockTick,long baseTick,List<Slot> slots,boolean allowed) {}
    private TrafficEngine.Flight flight(Map<String,Object> task,long departure) {
        return new TrafficEngine.Flight(s(task,"id"),s(task,"title"),s(task,"aircraftId"),departure,routes.current(s(task,"id"),true).points());
    }
    public List<TrafficEngine.Flight> obstacles(long clock) {
        var result=new ArrayList<TrafficEngine.Flight>();
        for(var t:db.rows("SELECT * FROM st_task WHERE status='executing' ORDER BY id FOR SHARE"))
            result.add(flight(t,clock-((Number)t.get("elapsedSeconds")).longValue()));
        for(var slot:db.rows("SELECT s.departure_tick,t.* FROM st_traffic_slot s JOIN st_task t ON t.id=s.task_id WHERE s.status='reserved' AND t.status='assigned' ORDER BY s.departure_tick,t.id FOR SHARE"))
            result.add(flight(slot,((Number)slot.get("departureTick")).longValue()));
        require(result.size()<=200,"活动飞行与预约超过200项，暂停新增起飞，请先释放预约");return result;
    }
    public List<String> constraints(Map<String,Object> task,Map<String,Object> aircraft,LocalDateTime departure) {
        var reasons=new ArrayList<String>();
        if(!"assigned".equals(s(task,"status")) || !"assigned".equals(s(aircraft,"status")) || FlightRoutes.n(aircraft,"deleted")!=0) reasons.add("任务或飞行器不再处于已分配状态");
        if(db.count("SELECT COUNT(*) FROM st_position_device WHERE aircraft_id=? AND enabled=1",aircraft.get("id"))>0) reasons.add("飞行器终端定位已启用，不能执行仿真任务");
        var orders=db.rows("SELECT deadline_at FROM st_logistics_order WHERE task_id=?",task.get("id"));
        var deadline=orders.isEmpty()?null:LocalDateTime.parse(s(orders.get(0),"deadlineAt"));
        reasons.addAll(DispatchOptimizer.constraintReasons(s(task,"type"),FlightRoutes.n(task,"durationSeconds"),FlightRoutes.n(task,"payload"),
            (int)FlightRoutes.n(task,"passengers"),deadline,DispatchOptimizer.vehicle(aircraft),departure));
        reasons.addAll(airspace.inspectLockedAt(s(task,"id"),departure).violations().stream().map(AirspaceEngine.Violation::reason).distinct().toList());
        return reasons;
    }
    public void assertLaunch(Map<String,Object> task,String actor) {
        long clock=tick();String id=s(task,"id");
        var own=db.rows("SELECT * FROM st_traffic_slot WHERE task_id=? AND status='reserved' FOR SHARE",id);
        require(own.isEmpty() || ((Number)own.get(0).get("departureTick")).longValue()<=clock,"该任务已预约错峰起飞，尚未到达仿真起飞时刻；可在多机协同页取消预约");
        var candidate=flight(task,clock);var others=obstacles(clock);
        require(TrafficEngine.hasLaunchCapacity(id,others),"活动飞行与预约最多200项，不能再新增起飞");
        var conflicts=TrafficEngine.conflicts(candidate,others,clock);
        records.save(id,conflicts.isEmpty(),Map.of("clockTick",clock,"candidate",candidate,"others",others,"conflicts",conflicts,
            "horizontalMeters",TrafficEngine.HORIZONTAL_METERS,"projectionBufferMeters",TrafficEngine.PROJECTION_BUFFER_METERS,"verticalMeters",TrafficEngine.VERTICAL_METERS),actor);
        require(conflicts.isEmpty(),"多机时空冲突：与「"+(conflicts.isEmpty()?"":conflicts.get(0).otherTitle())+"」航线间隔不足，请到多机协同页生成错峰方案");
    }
    public static void assertNotReserved(SkyRepository db,String id) {
        require(db.rows("SELECT task_id FROM st_traffic_slot WHERE task_id=? AND status='reserved' FOR SHARE",id).isEmpty(),"任务已预约错峰起飞，请先在多机协同页取消预约，再修改航线");
    }
    private Proposal evaluate(TrafficInputs.Preview input) {
        var ids=input.tasks().stream().map(TrafficInputs.Selection::taskId).toList();
        require(new HashSet<>(ids).size()==ids.size(),"不能重复选择同一任务");
        for(String id:ids.stream().sorted().toList()) db.one("SELECT id FROM st_task WHERE id=? FOR UPDATE",id);
        var tasks=input.tasks().stream().map(x->db.one("SELECT * FROM st_task WHERE id=? FOR UPDATE",x.taskId())).toList();
        for(String id:tasks.stream().map(x->s(x,"aircraftId")).sorted().toList()) {
            require(!id.isEmpty(),"请先为所有任务分配飞行器");db.one("SELECT id FROM st_aircraft WHERE id=? FOR UPDATE",id);
        }
        long clock=tick(),base=clock+input.leadSeconds();var now=LocalDateTime.now();
        var others=new ArrayList<>(obstacles(clock));var slots=new ArrayList<Slot>();
        for(int index=0;index<tasks.size();index++) {
            var task=tasks.get(index);String id=s(task,"id");assertNotReserved(db,id);
            require("assigned".equals(s(task,"status")),"仅已分配任务可以预约起飞");
            var route=routes.current(id,true);
            require(route.revision()==input.tasks().get(index).expectedRevision(),"任务航线版本已变化，请刷新后重新预览");
            var a=db.one("SELECT * FROM st_aircraft WHERE id=? FOR UPDATE",task.get("aircraftId"));
            var path=route.points();String title=s(task,"title"),aircraft=s(task,"aircraftId");
            var baseline=TrafficEngine.conflicts(flight(task,base),others,clock);
            int chosen=-1;var problems=new ArrayList<String>();
            for(int delay=0;delay<=input.maxDelaySeconds();delay++) {
                if(!TrafficEngine.conflicts(new TrafficEngine.Flight(id,title,aircraft,base+delay,path),others,clock).isEmpty()) continue;
                var reasons=constraints(task,a,now.plusSeconds(input.leadSeconds()+delay));
                if(reasons.isEmpty()) { chosen=delay;break; }
                problems.clear();problems.addAll(reasons);
            }
            if(chosen<0 && problems.isEmpty()) problems.add("在最大错峰等待时间内未找到安全时隙；请增加等待、调整航线或减少任务");
            var slot=new Slot(id,s(task,"title"),s(task,"aircraftId"),route.revision(),route.durationSeconds(),chosen,
                chosen<0?-1:base+chosen,chosen>=0,baseline,List.copyOf(problems));slots.add(slot);
            if(chosen>=0) others.add(flight(task,base+chosen));
        }
        return new Proposal(clock,base,slots,slots.stream().allMatch(Slot::allowed));
    }
    @Transactional
    public Map<String,Object> preview(TrafficInputs.Preview input,String actor) {
        lock(db);var result=evaluate(input);String id="TP-"+UUID.randomUUID().toString().replace("-","");
        db.update("INSERT INTO st_traffic_plan(id,request_json,result_json,created_by,expires_at) VALUES(?,?,?,?,?)",id,json(input),json(result),actor,LocalDateTime.now().plusMinutes(5));return detail(id);
    }
    @Transactional
    public Map<String,Object> confirm(String id,TrafficInputs.Confirm input,String actor) {
        lock(db);var row=db.one("SELECT * FROM st_traffic_plan WHERE id=? FOR UPDATE",id);
        require("proposed".equals(s(row,"status")),"方案已确认，不能重复预约");
        require(LocalDateTime.now().isBefore(LocalDateTime.parse(s(row,"expiresAt"))),"方案已过期，请重新生成");
        var old=parse(s(row,"resultJson"),Proposal.class);require(old.allowed(),"方案存在不可执行任务，请调整后重新生成");
        var result=evaluate(parse(s(row,"requestJson"),TrafficInputs.Preview.class));
        require(result.allowed(),"当前约束不再允许此方案，请重新预览");
        for(int i=0;i<old.slots().size();i++) {
            var a=old.slots().get(i);var b=result.slots().get(i);
            require(a.delaySeconds()==b.delaySeconds() && a.aircraftId().equals(b.aircraftId()),"资源或错峰时间已变化，请重新预览后确认");
        }
        require(obstacles(result.clockTick()).size()+result.slots().size()<=200,"活动飞行与预约最多200项");
        for(var slot:result.slots()) {
            db.update("INSERT INTO st_traffic_slot(task_id,plan_id,route_revision,aircraft_id,departure_tick,duration_seconds) VALUES(?,?,?,?,?,?) ON DUPLICATE KEY UPDATE plan_id=VALUES(plan_id),route_revision=VALUES(route_revision),aircraft_id=VALUES(aircraft_id),departure_tick=VALUES(departure_tick),duration_seconds=VALUES(duration_seconds),status='reserved',message='',updated_time=NOW(3)",
                slot.taskId(),id,slot.routeRevision(),slot.aircraftId(),slot.departureTick(),slot.durationSeconds());
            db.update("INSERT INTO st_audit(entity_id,action,reason,actor) VALUES(?,'traffic.reserve',?,?)",slot.taskId(),input.reason(),actor);
        }
        db.update("UPDATE st_traffic_plan SET status='confirmed',result_json=?,confirmed_by=?,confirmed_at=NOW(3),reason=? WHERE id=?",json(result),actor,input.reason(),id);return detail(id);
    }
    @Transactional
    public void cancel(String taskId,TrafficInputs.Confirm input,String actor) {
        lock(db);db.one("SELECT id FROM st_task WHERE id=? FOR UPDATE",taskId);
        require(db.update("UPDATE st_traffic_slot SET status='cancelled',message=?,updated_time=NOW(3) WHERE task_id=? AND status='reserved'",input.reason(),taskId)==1,"仅等待起飞的预约可以取消；已起飞请使用任务终止");
        db.update("INSERT INTO st_audit(entity_id,action,reason,actor) VALUES(?,'traffic.cancel',?,?)",taskId,input.reason(),actor);
    }
    @Transactional(readOnly=true)
    public Map<String,Object> state() {
        return Map.of("clockTick",db.count("SELECT tick FROM st_traffic_clock WHERE id=1"),"serverTime",LocalDateTime.now().toString(),"horizontalMeters",TrafficEngine.HORIZONTAL_METERS,"projectionBufferMeters",TrafficEngine.PROJECTION_BUFFER_METERS,"verticalMeters",TrafficEngine.VERTICAL_METERS,
            "slots",db.rows("SELECT s.*,t.title,t.status task_status FROM st_traffic_slot s JOIN st_task t ON t.id=s.task_id ORDER BY s.updated_time DESC LIMIT 200"),
            "plans",db.rows("SELECT id,status,created_by,created_time,confirmed_at FROM st_traffic_plan ORDER BY created_time DESC LIMIT 20"),
            "checks",db.rows("SELECT id,task_id,allowed,created_by,created_time FROM st_traffic_check ORDER BY created_time DESC LIMIT 100"));
    }
    public Map<String,Object> detail(String id) {
        var row=db.one("SELECT * FROM st_traffic_plan WHERE id=?",id);row.put("request",parse(s(row,"requestJson"),TrafficInputs.Preview.class));row.remove("requestJson");
        row.put("result",parse(s(row,"resultJson"),Proposal.class));row.remove("resultJson");return row;
    }
    public Map<String,Object> checkDetail(String id) {
        var row=db.one("SELECT * FROM st_traffic_check WHERE id=?",id);row.put("evidence",parse(s(row,"detailsJson"),Map.class));row.remove("detailsJson");return row;
    }
}
