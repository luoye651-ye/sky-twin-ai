package com.ruoyi.skytwin;
import java.util.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import static com.ruoyi.skytwin.OperationsRules.*;

@Service
public class TaskOperationsService {
    private final SkyRepository db;private final SkyService sky;private final LogisticsService logistics;private final EnvironmentService environment;private final RouteService routes;private final FlightRoutes flightRoutes;
    public TaskOperationsService(SkyRepository db,SkyService sky,LogisticsService logistics,EnvironmentService environment,RouteService routes,FlightRoutes flightRoutes){this.db=db;this.sky=sky;this.logistics=logistics;this.environment=environment;this.routes=routes;this.flightRoutes=flightRoutes;}
    public Map<String,Object> tasks(int page,int size,String state,String type,String keyword){
        var args=new ArrayList<Object>();String where=" WHERE 1=1";
        for(var filter:List.of(Map.entry("status",state),Map.entry("type",type))){if(!filter.getValue().isBlank()){where+=" AND t."+filter.getKey()+"=?";args.add(filter.getValue());}}
        require(keyword.length()<=200,"搜索文字最多200字符");
        if(!keyword.isBlank()){where+=" AND (t.title LIKE ? OR t.id=?)";args.add("%"+keyword+"%");args.add(keyword);}
        return page(db,"SELECT t.*,r.source_task_id,o.deadline_at,CASE WHEN t.status IN('completed','failed','cancelled') THEN '' WHEN o.deadline_at<NOW() THEN '配送时限已过' WHEN t.status='created' AND t.created_time<DATE_SUB(NOW(),INTERVAL 30 MINUTE) THEN '待分配超过30分钟' WHEN t.status='assigned' AND t.updated_time<DATE_SUB(NOW(),INTERVAL 10 MINUTE) THEN '待执行超过10分钟' WHEN t.status='executing' AND t.updated_time<DATE_SUB(NOW(),INTERVAL 60 SECOND) THEN '执行状态超过60秒未更新' ELSE '' END reminder ",
            "FROM st_task t LEFT JOIN st_task_retry r ON r.task_id=t.id LEFT JOIN st_logistics_order o ON o.task_id=t.id",where,args,page,size," ORDER BY t.created_time DESC,t.id DESC");
    }
    @Transactional
    public Map<String,Object> retry(String source,OperationsInputs.Retry input,String actor){
        uuid(input.requestId());TrafficService.lock(db);
        String hash=EnvironmentImage.hash((source+"\n"+input.reason()+"\n"+input.deadlineMinutes()).getBytes(java.nio.charset.StandardCharsets.UTF_8));
        var previous=db.rows("SELECT * FROM st_task_retry WHERE request_id=? FOR UPDATE",input.requestId());
        if(!previous.isEmpty()){var old=previous.get(0);require(actor.equals(s(old,"createdBy"))&&source.equals(s(old,"sourceTaskId"))&&hash.equals(s(old,"requestHash")),"请求编号内容已改变");return old;}
        var task=db.one("SELECT * FROM st_task WHERE id=? FOR UPDATE",source);
        require(Set.of("failed","cancelled").contains(s(task,"status")),"仅失败或取消任务可创建重试任务");
        require(db.count("SELECT COUNT(*) FROM st_task_retry r JOIN st_task t ON t.id=r.task_id WHERE r.source_task_id=? AND t.status IN('created','assigned','executing')",source)==0,"已有未结束的重试任务，请勿重复创建");
        require(db.count("SELECT COUNT(*) FROM st_commute_flight WHERE task_id=?",source)==0,"通勤班次请取消原班次并另建班次，保留预约历史");
        String child;var linked=db.rows("SELECT discovery_id FROM st_env_response WHERE task_id=?",source);
        if(!linked.isEmpty()){
            var detail=environment.respond(s(linked.get(0),"discoveryId"),new EnvironmentInputs.Response(s(task,"startStationId"),s(task,"endStationId"),input.reason()),actor);
            var responses=(List<?>)detail.get("responses");child=Objects.toString(((Map<?,?>)responses.get(responses.size()-1)).get("taskId"));
        }else{
            var orders=db.rows("SELECT * FROM st_logistics_order WHERE task_id=?",source);
            if(!orders.isEmpty()){
                var order=orders.get(0);String orderId=logistics.create(new LogisticsInputs.Create(s(order,"cargoName"),n(order,"weight"),s(task,"startStationId"),s(task,"endStationId"),input.deadlineMinutes(),input.reason()),actor);
                child=s(db.one("SELECT task_id FROM st_logistics_order WHERE id=?",orderId),"taskId");
            }else child=sky.createTask(new SkyInputs.Task(s(task,"title"),s(task,"type"),s(task,"startStationId"),s(task,"endStationId"),n(task,"payload"),(int)n(task,"passengers"),n(task,"speed"),n(task,"cruiseAltitude"),input.reason()),actor);
            var original=flightRoutes.current(source,false);
            if(!original.waypoints().isEmpty())routes.save(child,new RouteInputs.Save(1,original.waypoints().stream().map(p->new RouteInputs.Waypoint(p.longitude(),p.latitude())).toList(),input.reason()),actor);
        }
        db.update("INSERT INTO st_task_retry(request_id,source_task_id,task_id,created_by,reason,request_hash) VALUES(?,?,?,?,?,?)",input.requestId(),source,child,actor,input.reason(),hash);
        audit(db,child,"task.retry",input.reason(),actor);
        return Map.of("taskId",child,"sourceTaskId",source);
    }
}
