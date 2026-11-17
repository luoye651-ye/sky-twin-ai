package com.ruoyi.skytwin;

import java.time.LocalDateTime;
import java.util.*;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.common.exception.ServiceException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class DispatchService {
    private final SkyRepository db;
    private final SkyService sky;
    private final ObjectMapper mapper;
    private final AirspaceService airspace;
    private final FlightRoutes routes;
    public DispatchService(SkyRepository db,SkyService sky,ObjectMapper mapper,AirspaceService airspace,FlightRoutes routes) { this.db=db;this.sky=sky;this.mapper=mapper;this.airspace=airspace;this.routes=routes; }
    private static void require(boolean condition,String message) { if(!condition) throw new ServiceException(message,409); }
    private static String text(Map<String,Object> row,String key) { return Objects.toString(row.get(key),""); }
    private static double number(Map<String,Object> row,String key) { return ((Number)row.get(key)).doubleValue(); }
    private String json(Object value) {
        try { return mapper.writeValueAsString(value); }
        catch(JsonProcessingException ex) { throw new IllegalStateException("调度记录序列化失败",ex); }
    }
    private <T> T parse(String value,Class<T> type) {
        try { return mapper.readValue(value,type); }
        catch(JsonProcessingException ex) { throw new IllegalStateException("调度记录读取失败",ex); }
    }
    private static final String TASK_SQL="SELECT t.*,s.longitude start_lon,s.latitude start_lat,s.type start_type,e.type end_type,"
        +"s.status start_status,e.status end_status,s.deleted start_deleted,e.deleted end_deleted,o.deadline_at,er.priority response_priority "
        +"FROM st_task t JOIN st_station s ON s.id=t.start_station_id JOIN st_station e ON e.id=t.end_station_id "
        +"LEFT JOIN st_logistics_order o ON o.task_id=t.id LEFT JOIN st_env_response er ON er.task_id=t.id WHERE t.id=?";
    private DispatchOptimizer.Job job(String id,int priority) {
        var row=db.one(TASK_SQL,id);
        if(row.get("responsePriority") instanceof Number floor) priority=Math.max(priority,floor.intValue());
        boolean enabled="enabled".equals(text(row,"startStatus")) && "enabled".equals(text(row,"endStatus"))
            && number(row,"startDeleted")==0 && number(row,"endDeleted")==0;
        if("commute".equals(text(row,"type"))) enabled &= "vertiport".equals(text(row,"startType")) && "vertiport".equals(text(row,"endType"));
        return new DispatchOptimizer.Job(id,text(row,"title"),text(row,"type"),number(row,"payload"),(int)number(row,"passengers"),
            (int)number(row,"durationSeconds"),number(row,"startLon"),number(row,"startLat"),
            row.get("deadlineAt")==null?null:LocalDateTime.parse(text(row,"deadlineAt")),priority,text(row,"status"),enabled);
    }
    @Transactional
    public Map<String,Object> preview(DispatchInputs.Preview input,String actor) {
        var ids=input.tasks().stream().map(DispatchInputs.Selection::taskId).toList();
        require(new HashSet<>(ids).size()==ids.size(),"不能重复选择同一任务");
        var jobs=input.tasks().stream().map(x->job(x.taskId(),x.priority())).toList();
        require(jobs.stream().allMatch(x->"created".equals(x.status())),"仅待分配任务可生成方案，请刷新任务列表");
        var rows=db.rows("SELECT * FROM st_aircraft WHERE deleted=0 ORDER BY id");
        if(input.aircraftIds()!=null) {
            var selected=new HashSet<>(input.aircraftIds());
            require(!selected.isEmpty() && selected.size()==input.aircraftIds().size(),"请选择不重复的飞行器资源");
            rows=rows.stream().filter(x->selected.contains(text(x,"id"))).toList();
            require(rows.size()==selected.size(),"所选飞行器不存在或已移除");
        }
        require(rows.size()<=200,"单次最多评估200架飞行器，请限定资源范围");
        // Preserve the resource in decisions, but mark it unavailable to the optimizer.
        var external=db.rows("SELECT aircraft_id FROM st_position_device WHERE enabled=1").stream().map(x->text(x,"aircraftId")).collect(java.util.stream.Collectors.toSet());
        for(var row:rows) if(external.contains(text(row,"id"))) row.put("status","terminal_positioning");
        var now=LocalDateTime.now();
        var routeReasons=new HashMap<String,List<String>>();
        for(var job:jobs) routeReasons.put(job.id(),airspace.inspect(job.id(),now).violations().stream().map(AirspaceEngine.Violation::reason).distinct().toList());
        var result=DispatchOptimizer.solve(jobs,rows.stream().map(DispatchOptimizer::vehicle).toList(),now,routeReasons);
        String id="DP-"+UUID.randomUUID().toString().replace("-","");
        db.update("INSERT INTO st_dispatch_plan(id,algorithm,request_json,result_json,created_by,created_time,expires_at) VALUES(?,?,?,?,?,?,?)",
            id,DispatchOptimizer.VERSION,json(input),json(result),actor,now,now.plusMinutes(5));
        for(var job:jobs) db.update("INSERT INTO st_dispatch_route_snapshot(plan_id,task_id,route_revision) VALUES(?,?,?)",id,job.id(),routes.current(job.id(),false).revision());
        db.update("INSERT INTO st_audit(entity_id,action,reason,actor) VALUES(?,'dispatch.preview',?,?)",id,"生成集群调度方案："+result.assignments().size()+"项分配",actor);
        return detail(id);
    }
    @Transactional
    public Map<String,Object> confirm(String id,DispatchInputs.Confirm input,String actor) {
        TrafficService.lock(db);
        var plan=db.one("SELECT * FROM st_dispatch_plan WHERE id=? FOR UPDATE",id);
        require("proposed".equals(text(plan,"status")),"方案已确认，不能重复派机");
        require(LocalDateTime.now().isBefore(LocalDateTime.parse(text(plan,"expiresAt"))),"方案已过期，请重新生成");
        var result=parse(text(plan,"resultJson"),DispatchOptimizer.Result.class);
        require(!result.assignments().isEmpty(),"该方案没有可执行的分配");
        var assignments=result.assignments().stream().sorted(Comparator.comparing(DispatchOptimizer.Assignment::taskId)).toList();
        // Task -> aircraft lock order matches SkyService. Recheck after acquiring locks;
        // any later validation/audit failure rolls back every assignment and the plan.
        for(var assignment:assignments) db.one("SELECT id FROM st_task WHERE id=? FOR UPDATE",assignment.taskId());
        for(var aircraftId:assignments.stream().map(DispatchOptimizer.Assignment::aircraftId).sorted().toList())
            db.one("SELECT id FROM st_aircraft WHERE id=? AND deleted=0 FOR UPDATE",aircraftId);
        for(var assignment:assignments) {
            var current=job(assignment.taskId(),assignment.priority());
            var revisions=db.rows("SELECT route_revision FROM st_dispatch_route_snapshot WHERE plan_id=? AND task_id=?",id,assignment.taskId());
            require(!revisions.isEmpty() && ((Number)revisions.get(0).get("routeRevision")).intValue()==routes.current(assignment.taskId(),true).revision(),"任务航线已变化，请重新生成调度方案");
            require(current.stationsEnabled(),"站点状态已变化，请重新生成方案");
            airspace.assertAllowed(assignment.taskId(),"dispatch_confirm",actor);
            sky.taskAction(assignment.taskId(),"assign",new SkyInputs.Action(assignment.aircraftId(),input.reason()),actor);
        }
        db.update("UPDATE st_dispatch_plan SET status='confirmed',confirmed_by=?,confirmed_at=NOW(3),reason=? WHERE id=?",actor,input.reason(),id);
        db.update("INSERT INTO st_audit(entity_id,action,reason,actor) VALUES(?,'dispatch.confirm',?,?)",id,input.reason(),actor);
        return detail(id);
    }
    public List<Map<String,Object>> history() {
        return db.rows("SELECT id,algorithm,status,created_by,created_time,expires_at,confirmed_by,confirmed_at,reason FROM st_dispatch_plan ORDER BY created_time DESC,id DESC LIMIT 20");
    }
    public Map<String,Object> detail(String id) {
        var row=db.one("SELECT * FROM st_dispatch_plan WHERE id=?",id);
        row.put("request",parse(text(row,"requestJson"),DispatchInputs.Preview.class));row.remove("requestJson");
        row.put("result",parse(text(row,"resultJson"),DispatchOptimizer.Result.class));row.remove("resultJson");
        row.put("serverTime",LocalDateTime.now().toString());return row;
    }
}
