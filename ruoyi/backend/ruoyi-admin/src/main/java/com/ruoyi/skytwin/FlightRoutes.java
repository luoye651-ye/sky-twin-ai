package com.ruoyi.skytwin;

import java.util.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Component;

/** Persistence/projection only, with no dependency on SkyService or policy decisions. */
@Component
public class FlightRoutes {
    private final SkyRepository db;private final ObjectMapper mapper;
    public FlightRoutes(SkyRepository db,ObjectMapper mapper) { this.db=db;this.mapper=mapper; }
    public static double n(Map<String,Object> row,String key) { return ((Number)row.get(key)).doubleValue(); }
    public Map<String,Object> task(String id,boolean locked) {
        return db.one("SELECT t.*,s.longitude start_lon,s.latitude start_lat,e.longitude end_lon,e.latitude end_lat FROM st_task t JOIN st_station s ON s.id=t.start_station_id JOIN st_station e ON e.id=t.end_station_id WHERE t.id=?"+(locked?" FOR SHARE":""),id);
    }
    public RouteEngine.Plan candidate(Map<String,Object> task,int revision,List<RouteEngine.Waypoint> via,Integer legacyDuration) {
        return RouteEngine.build(revision,new RouteEngine.Waypoint(n(task,"startLon"),n(task,"startLat")),new RouteEngine.Waypoint(n(task,"endLon"),n(task,"endLat")),via,n(task,"speed"),n(task,"cruiseAltitude"),legacyDuration);
    }
    public RouteEngine.Plan current(String id,boolean locked) {
        var rows=db.rows("SELECT plan_json FROM st_task_route WHERE task_id=? ORDER BY revision DESC LIMIT 1"+(locked?" FOR SHARE":""),id);
        if(!rows.isEmpty()) return parse(Objects.toString(rows.get(0).get("planJson")));
        return legacy(task(id,locked));
    }
    private RouteEngine.Plan legacy(Map<String,Object> row) { return RouteEngine.legacy(new RouteEngine.Waypoint(n(row,"startLon"),n(row,"startLat")),new RouteEngine.Waypoint(n(row,"endLon"),n(row,"endLat")),n(row,"speed"),n(row,"cruiseAltitude"),(int)n(row,"durationSeconds")); }
    public RouteEngine.Plan parse(String json) {
        try { return mapper.readValue(json,RouteEngine.Plan.class); } catch(Exception e) { throw new IllegalStateException("航线记录读取失败",e); }
    }
    public void store(String taskId,RouteEngine.Plan plan,String reason,String actor) {
        try {
            String json=mapper.writeValueAsString(plan);
            db.update("INSERT INTO st_task_route(id,task_id,revision,plan_json,reason,created_by) VALUES(?,?,?,?,?,?)","RT-"+UUID.randomUUID().toString().replace("-",""),taskId,plan.revision(),json,reason,actor);
        } catch(com.fasterxml.jackson.core.JsonProcessingException e) { throw new IllegalStateException("航线记录保存失败",e); }
    }
    public List<Map<String,Object>> attach(List<Map<String,Object>> tasks) {
        if(tasks.isEmpty()) return tasks;
        var latest=new HashMap<String,RouteEngine.Plan>();
        String placeholders=String.join(",",Collections.nCopies(tasks.size(),"?"));
        for(var row:db.rows("SELECT r.task_id,r.plan_json FROM st_task_route r WHERE r.task_id IN ("+placeholders+") AND r.revision=(SELECT MAX(x.revision) FROM st_task_route x WHERE x.task_id=r.task_id)",tasks.stream().map(t->t.get("id")).toArray())) latest.put(Objects.toString(row.get("taskId")),parse(Objects.toString(row.get("planJson"))));
        for(var task:tasks) {
            var route=latest.get(Objects.toString(task.get("id")));
            if(route==null) route=legacy(task);
            task.put("routeRevision",route.revision());task.put("routePoints",route.points());task.put("routeDistanceMeters",route.distanceMeters());
            task.put("navigation",FlightNavigation.at(route,n(task,"elapsedSeconds"),Objects.toString(task.get("status"))));
            for(String key:List.of("startLon","startLat","endLon","endLat")) task.remove(key);
        }
        return tasks;
    }
}
