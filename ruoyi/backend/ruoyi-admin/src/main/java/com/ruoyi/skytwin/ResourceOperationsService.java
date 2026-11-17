package com.ruoyi.skytwin;
import java.util.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import static com.ruoyi.skytwin.OperationsRules.*;

@Service
public class ResourceOperationsService {
    private final SkyRepository db;private final SkyService sky;
    public ResourceOperationsService(SkyRepository db,SkyService sky){this.db=db;this.sky=sky;}
    public Map<String,Object> history(int page,int size){return page(db,"SELECT r.*,a.name aircraft_name ","FROM st_resource_operation r JOIN st_aircraft a ON a.id=r.aircraft_id","",List.of(),page,size," ORDER BY r.created_time DESC,r.id DESC");}
    @Transactional public Map<String,Object> start(OperationsInputs.Resource input,String actor){
        uuid(input.requestId());require(Set.of("charging","maintenance","fault").contains(input.kind()),"运维类型无效");TrafficService.lock(db);
        var prior=db.rows("SELECT * FROM st_resource_operation WHERE request_id=? FOR UPDATE",input.requestId());
        if(!prior.isEmpty()){var r=prior.get(0);require(actor.equals(s(r,"createdBy"))&&input.aircraftId().equals(s(r,"aircraftId"))&&input.kind().equals(s(r,"kind"))&&input.reason().equals(s(r,"reason")),"请求编号已用于其他运维内容");return r;}
        var active=db.rows("SELECT id FROM st_task WHERE aircraft_id=? AND status IN('assigned','executing') ORDER BY id FOR UPDATE",input.aircraftId());
        require(active.isEmpty()||input.kind().equals("fault"),"任务占用中不能充电或维护");
        for(var task:active)sky.taskAction(s(task,"id"),"fail",new SkyInputs.Action(null,input.reason()),actor);
        var aircraft=db.one("SELECT * FROM st_aircraft WHERE id=? AND deleted=0 FOR UPDATE",input.aircraftId());
        PositionService.assertSimulationAvailable(db,input.aircraftId());
        require("idle".equals(s(aircraft,"status")),"已有运维或飞机状态不可操作");
        String id=id("MO-");db.update("INSERT INTO st_resource_operation(id,request_id,aircraft_id,kind,reason,initial_battery,created_by) VALUES(?,?,?,?,?,?,?)",id,input.requestId(),input.aircraftId(),input.kind(),input.reason(),aircraft.get("battery"),actor);
        db.update("UPDATE st_aircraft SET status=? WHERE id=?",input.kind(),input.aircraftId());audit(db,id,"resource.start",input.reason(),actor);
        return db.one("SELECT * FROM st_resource_operation WHERE id=?",id);
    }
    @Transactional public Map<String,Object> close(String id,OperationsInputs.Close input,String actor){
        require(Double.isFinite(input.battery())&&input.battery()>=0&&input.battery()<=100,"电量范围无效");TrafficService.lock(db);
        var operation=db.one("SELECT * FROM st_resource_operation WHERE id=? FOR UPDATE",id);require("active".equals(s(operation,"status")),"运维记录已结束");
        var aircraft=db.one("SELECT * FROM st_aircraft WHERE id=? FOR UPDATE",operation.get("aircraftId"));require(s(aircraft,"status").equals(s(operation,"kind")),"资源状态已变化");
        double battery=n(aircraft,"battery");if("charging".equals(s(operation,"kind"))){require(input.battery()>=battery,"充电完成值不能低于原电量");battery=input.battery();}
        db.update("UPDATE st_aircraft SET status='idle',battery=? WHERE id=?",battery,operation.get("aircraftId"));
        db.update("UPDATE st_resource_operation SET status='closed',final_battery=?,resolution=?,closed_by=?,closed_time=NOW(3) WHERE id=?",battery,input.reason(),actor,id);
        audit(db,id,"resource.close",input.reason(),actor);return db.one("SELECT * FROM st_resource_operation WHERE id=?",id);
    }
    public List<Map<String,Object>> stations(){return db.rows("SELECT s.*,COALESCE(c.capacity,200) capacity,(SELECT COUNT(*) FROM st_task t WHERE t.status='executing' AND (t.start_station_id=s.id OR t.end_station_id=s.id)) occupied FROM st_station s LEFT JOIN st_station_capacity c ON c.station_id=s.id WHERE s.deleted=0 ORDER BY s.id");}
    @Transactional public void capacity(String id,OperationsInputs.Capacity input,String actor){
        require(input.capacity()>=1&&input.capacity()<=200,"容量范围1～200");TrafficService.lock(db);db.one("SELECT id FROM st_station WHERE id=? AND deleted=0 FOR UPDATE",id);
        require(db.count("SELECT COUNT(*) FROM st_task WHERE status='executing' AND (start_station_id=? OR end_station_id=?)",id,id)<=input.capacity(),"容量不能低于当前占用");
        require(db.count("SELECT COUNT(*) FROM st_commute_flight g WHERE g.status='scheduled' AND g.arrival_at>NOW() AND (g.start_station_id=? OR g.end_station_id=?) AND (SELECT COUNT(*) FROM st_commute_flight f WHERE f.status='scheduled' AND (f.start_station_id=? OR f.end_station_id=?) AND f.departure_at<DATE_ADD(g.arrival_at,INTERVAL 5 MINUTE) AND f.arrival_at>DATE_SUB(g.departure_at,INTERVAL 5 MINUTE))>?",id,id,id,id,input.capacity())==0,"容量不能低于已有未来班次的保守预约占用");
        db.update("INSERT INTO st_station_capacity(station_id,capacity,updated_by) VALUES(?,?,?) ON DUPLICATE KEY UPDATE capacity=VALUES(capacity),updated_by=VALUES(updated_by),updated_time=NOW(3)",id,input.capacity(),actor);
        audit(db,id,"station.capacity",input.reason(),actor);
    }
}
