package com.ruoyi.skytwin;

import java.time.LocalDateTime;
import java.util.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import com.ruoyi.common.exception.ServiceException;

@Service
public class RouteService {
    private final SkyRepository db;private final FlightRoutes routes;private final AirspaceService airspace;
    public RouteService(SkyRepository db,FlightRoutes routes,AirspaceService airspace) { this.db=db;this.routes=routes;this.airspace=airspace; }
    private static void require(boolean ok,String message) { if(!ok) throw new ServiceException(message,409); }
    public Map<String,Object> detail(String id) {
        var task=routes.task(id,false);
        return Map.of("taskId",id,"title",task.get("title"),"status",task.get("status"),"plan",routes.current(id,false),"versions",db.rows("SELECT revision,reason,created_by,created_time FROM st_task_route WHERE task_id=? ORDER BY revision DESC",id));
    }
    public RouteEngine.Plan version(String id,int revision) {
        return routes.parse(Objects.toString(db.one("SELECT plan_json FROM st_task_route WHERE task_id=? AND revision=?",id,revision).get("planJson")));
    }
    private Map<String,Object> evaluate(String id,RouteInputs.Save input,boolean save,String actor) {
        // Traffic clock -> task -> aircraft -> policy. Reservations freeze their route version.
        TrafficService.lock(db);
        var task=db.one("SELECT * FROM st_task WHERE id=? FOR UPDATE",id);
        TrafficService.assertNotReserved(db,id);
        require(Set.of("created","assigned").contains(task.get("status")),"仅待分配或已分配任务可以规划航线；执行中和结束后不可修改");
        var current=routes.current(id,true);
        require(current.revision()==input.expectedRevision(),"航线版本已变化，请重新加载后再规划（草稿未覆盖服务端）");
        RouteEngine.Plan candidate;
        try { candidate=routes.candidate(routes.task(id,true),current.revision()+1,input.waypoints().stream().map(p->new RouteEngine.Waypoint(p.longitude(),p.latitude())).toList(),null); }
        catch(IllegalArgumentException e) { throw new ServiceException(e.getMessage(),409); }
        var linked=db.rows("SELECT d.longitude,d.latitude FROM st_env_response r JOIN st_env_discovery d ON d.id=r.discovery_id WHERE r.task_id=?",id);
        if(!linked.isEmpty()) require(EnvironmentRules.visits(candidate.points(),FlightRoutes.n(linked.get(0),"longitude"),FlightRoutes.n(linked.get(0),"latitude")),"应急侦察航线必须保留事件上空航点（10m范围内），不能绕过事件点后结案");
        var constraints=new ArrayList<String>();
        var orders=db.rows("SELECT deadline_at FROM st_logistics_order WHERE task_id=?",id);
        LocalDateTime deadline=orders.isEmpty()?null:LocalDateTime.parse(Objects.toString(orders.get(0).get("deadlineAt")));
        var now=LocalDateTime.now();
        if(task.get("aircraftId")!=null) {
            var a=db.one("SELECT * FROM st_aircraft WHERE id=? AND deleted=0 FOR UPDATE",task.get("aircraftId"));
            PositionService.assertSimulationAvailable(db,Objects.toString(a.get("id")));
            constraints.addAll(DispatchOptimizer.constraintReasons(Objects.toString(task.get("type")),candidate.durationSeconds(),FlightRoutes.n(task,"payload"),(int)FlightRoutes.n(task,"passengers"),deadline,DispatchOptimizer.vehicle(a),now));
        } else if(deadline!=null && now.plusSeconds(candidate.durationSeconds()).isAfter(deadline)) constraints.add("配送时限不足，绕行后预计仿真抵达时间晚于截止时间");
        var check=airspace.inspectPath(id,Objects.toString(task.get("title")),candidate.points(),save,actor);
        boolean allowed=check.allowed() && constraints.isEmpty();
        if(save) {
            var messages=new ArrayList<>(constraints);check.violations().stream().map(AirspaceEngine.Violation::reason).distinct().forEach(messages::add);
            require(allowed,String.join("；",messages));
            routes.store(id,candidate,input.reason(),actor);
            db.update("UPDATE st_task SET duration_seconds=?,updated_time=NOW(3) WHERE id=?",candidate.durationSeconds(),id);
            db.update("INSERT INTO st_audit(entity_id,action,reason,actor) VALUES(?,'route.save',?,?)",id,input.reason(),actor);
        }
        return Map.of("plan",candidate,"check",check,"constraints",constraints,"allowed",allowed,"saved",save,"serverTime",LocalDateTime.now().toString());
    }
    @Transactional public Map<String,Object> suggest(String id,RouteInputs.Save input,String actor) {
        TrafficService.lock(db);var task=routes.task(id,true);var current=routes.current(id,true);
        require(current.revision()==input.expectedRevision(),"航线版本已变化，请刷新");
        var exclusions=new ArrayList<DetourPlanner.Rect>();
        for(var zone:airspace.zones()) {
            boolean enabled=Boolean.TRUE.equals(zone.get("enabled")) || zone.get("enabled") instanceof Number n && n.intValue()!=0;
            double altitude=FlightRoutes.n(task,"cruiseAltitude");
            if(enabled && ("no_fly".equals(zone.get("type")) && altitude>=FlightRoutes.n(zone,"minAltitude") && altitude<=FlightRoutes.n(zone,"maxAltitude") || "height_limit".equals(zone.get("type")) && altitude>FlightRoutes.n(zone,"maxAltitude")))
                exclusions.add(new DetourPlanner.Rect(FlightRoutes.n(zone,"west"),FlightRoutes.n(zone,"south"),FlightRoutes.n(zone,"east"),FlightRoutes.n(zone,"north")));
        }
        var required=new ArrayList<RouteEngine.Waypoint>();required.add(new RouteEngine.Waypoint(FlightRoutes.n(task,"startLon"),FlightRoutes.n(task,"startLat")));
        required.addAll(current.waypoints());required.add(new RouteEngine.Waypoint(FlightRoutes.n(task,"endLon"),FlightRoutes.n(task,"endLat")));
        try{
            var via=DetourPlanner.plan(required,exclusions);var candidate=new RouteInputs.Save(current.revision(),via.stream().map(p->new RouteInputs.Waypoint(p.longitude(),p.latitude())).toList(),input.reason());
            var result=new LinkedHashMap<>(evaluate(id,candidate,false,actor));result.put("suggestedWaypoints",candidate.waypoints());result.put("notice","候选路线保留原有中间必经点，并保守避开全部启用矩形限制区；无建筑/地形避障或实机能力，需审查后另行保存");return result;
        }catch(IllegalArgumentException e){throw new ServiceException(e.getMessage(),409);}
    }
    @Transactional public Map<String,Object> preview(String id,RouteInputs.Save input,String actor) { return evaluate(id,input,false,actor); }
    @Transactional public Map<String,Object> save(String id,RouteInputs.Save input,String actor) { return evaluate(id,input,true,actor); }
}
