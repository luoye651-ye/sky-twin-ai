package com.ruoyi.skytwin;
import java.time.*;
import java.util.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import static com.ruoyi.skytwin.OperationsRules.*;

@Service
public class CommuteService {
    private final SkyRepository db;private final SkyService sky;
    public CommuteService(SkyRepository db,SkyService sky){this.db=db;this.sky=sky;}
    private static final String SELECT="SELECT f.*,t.status task_status,t.progress,CASE WHEN t.status='completed' THEN t.updated_time ELSE NULL END arrived_at,s.name start_station_name,e.name end_station_name,(SELECT COALESCE(SUM(b.seats),0) FROM st_commute_booking b WHERE b.flight_id=f.id AND b.status='confirmed') booked_seats ";
    private static final String FROM="FROM st_commute_flight f JOIN st_station s ON s.id=f.start_station_id JOIN st_station e ON e.id=f.end_station_id LEFT JOIN st_task t ON t.id=f.task_id";
    public Map<String,Object> list(int page,int size){return page(db,SELECT,FROM,"",List.of(),page,size," ORDER BY f.departure_at DESC,f.id DESC");}
    public Map<String,Object> detail(String id){var row=db.one(SELECT+FROM+" WHERE f.id=?",id);row.put("bookings",db.rows("SELECT * FROM st_commute_booking WHERE flight_id=? ORDER BY created_time,id",id));return row;}
    private void window(String start,String end,LocalDateTime departure,LocalDateTime arrival,String except){
        require(departure!=null&&departure.isAfter(LocalDateTime.now().minusMinutes(1))&&departure.isBefore(LocalDateTime.now().plusDays(30)),"班次时间应为当前至未来30天内");
        for(String station:java.util.stream.Stream.of(start,end).sorted().toList()){
            db.one("SELECT id FROM st_station WHERE id=? AND deleted=0 AND status='enabled' AND type='vertiport' FOR UPDATE",station);
            long overlap=db.count("SELECT COUNT(*) FROM st_commute_flight WHERE id<>? AND status='scheduled' AND (start_station_id=? OR end_station_id=?) AND departure_at<? AND arrival_at>?",except,station,station,arrival.plusMinutes(5),departure.minusMinutes(5));
            require(overlap<stationCapacity(db,station),"起降场班次预约容量不足，请调整出发时间");
        }
    }
    @Transactional public Map<String,Object> create(OperationsInputs.Flight input,String actor){
        uuid(input.requestId());require(!input.startStationId().equals(input.endStationId()),"起降场必须不同");require(input.seats()>=1&&input.seats()<=20,"座位范围1～20");TrafficService.lock(db);
        String hash=EnvironmentImage.hash(input.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8));var prior=db.rows("SELECT * FROM st_commute_flight WHERE request_id=? FOR UPDATE",input.requestId());
        if(!prior.isEmpty()){require(actor.equals(s(prior.get(0),"createdBy"))&&hash.equals(s(prior.get(0),"requestHash")),"班次请求内容已改变");return detail(s(prior.get(0),"id"));}
        var from=db.one("SELECT * FROM st_station WHERE id=?",input.startStationId());var to=db.one("SELECT * FROM st_station WHERE id=?",input.endStationId());
        var route=RouteEngine.build(1,new RouteEngine.Waypoint(n(from,"longitude"),n(from,"latitude")),new RouteEngine.Waypoint(n(to,"longitude"),n(to,"latitude")),List.of(),20,80,null);
        var arrival=input.departureAt().plusSeconds(route.durationSeconds());window(input.startStationId(),input.endStationId(),input.departureAt(),arrival,"");String id=id("CF-");
        db.update("INSERT INTO st_commute_flight(id,request_id,request_hash,title,start_station_id,end_station_id,departure_at,arrival_at,seats,created_by,reason) VALUES(?,?,?,?,?,?,?,?,?,?,?)",id,input.requestId(),hash,input.title(),input.startStationId(),input.endStationId(),input.departureAt(),arrival,input.seats(),actor,input.reason());
        audit(db,id,"commute.create",input.reason(),actor);return detail(id);
    }
    @Transactional public Map<String,Object> book(String id,OperationsInputs.Booking input,String actor){
        uuid(input.requestId());require(input.seats()>=1&&input.seats()<=20,"预约座位数无效");TrafficService.lock(db);var flight=db.one("SELECT * FROM st_commute_flight WHERE id=? FOR UPDATE",id);
        var prior=db.rows("SELECT * FROM st_commute_booking WHERE request_id=? FOR UPDATE",input.requestId());
        if(!prior.isEmpty()){var row=prior.get(0);require(actor.equals(s(row,"createdBy"))&&id.equals(s(row,"flightId"))&&input.seats()==(int)n(row,"seats"),"预约请求编号已用于其他内容");return row;}
        require("scheduled".equals(s(flight,"status"))&&flight.get("taskId")==null,"班次已锁定名单或取消，不能继续预约");
        require(LocalDateTime.now().isBefore(LocalDateTime.parse(s(flight,"departureAt"))),"已到计划出发时间，停止预约");
        long booked=db.count("SELECT COALESCE(SUM(seats),0) FROM st_commute_booking WHERE flight_id=? AND status='confirmed'",id);require(booked+input.seats()<=(int)n(flight,"seats"),"剩余座位不足，不能超卖");
        String booking=id("CB-");db.update("INSERT INTO st_commute_booking(id,request_id,flight_id,seats,created_by) VALUES(?,?,?,?,?)",booking,input.requestId(),id,input.seats(),actor);audit(db,id,"commute.book","预约座位："+input.seats(),actor);return db.one("SELECT * FROM st_commute_booking WHERE id=?",booking);
    }
    @Transactional public void cancelBooking(String id,String actor){
        TrafficService.lock(db);var booking=db.one("SELECT * FROM st_commute_booking WHERE id=?",id);var flight=db.one("SELECT * FROM st_commute_flight WHERE id=? FOR UPDATE",booking.get("flightId"));
        require(actor.equals(s(booking,"createdBy")),"只能取消本人创建的预约");require(flight.get("taskId")==null&&"scheduled".equals(s(flight,"status")),"名单已锁定，请由调度员处理班次取消");
        require("confirmed".equals(s(booking,"status")),"预约已取消");db.update("UPDATE st_commute_booking SET status='cancelled',cancelled_time=NOW(3) WHERE id=?",id);audit(db,s(booking,"flightId"),"commute.unbook","取消预约："+id,actor);
    }
    @Transactional public Map<String,Object> action(String id,String action,OperationsInputs.FlightAction input,String actor){
        TrafficService.lock(db);var flight=db.one("SELECT * FROM st_commute_flight WHERE id=? FOR UPDATE",id);require("scheduled".equals(s(flight,"status")),"班次已取消");require((int)n(flight,"revision")==input.expectedRevision(),"班次版本已改变，请刷新");
        String taskId=flight.get("taskId")==null?null:s(flight,"taskId");
        if(action.equals("delay")){
            require(taskId==null||Set.of("created","assigned").contains(s(db.one("SELECT status FROM st_task WHERE id=? FOR UPDATE",taskId),"status")),"执行中或结束班次不可改时");
            var previous=LocalDateTime.parse(s(flight,"departureAt"));long seconds=Duration.between(previous,LocalDateTime.parse(s(flight,"arrivalAt"))).getSeconds();
            require(input.departureAt()!=null,"请填写新出发时间");window(s(flight,"startStationId"),s(flight,"endStationId"),input.departureAt(),input.departureAt().plusSeconds(seconds),id);
            db.update("UPDATE st_commute_flight SET departure_at=?,arrival_at=?,revision=revision+1,reason=? WHERE id=?",input.departureAt(),input.departureAt().plusSeconds(seconds),input.reason(),id);
        }else if(action.equals("activate")){
            require(taskId==null,"班次已生成任务，不可重复激活");long seats=db.count("SELECT COALESCE(SUM(seats),0) FROM st_commute_booking WHERE flight_id=? AND status='confirmed'",id);require(seats>0,"无人预约，不能生成空载通勤任务");
            taskId=sky.createTask(new SkyInputs.Task(s(flight,"title"),"commute",s(flight,"startStationId"),s(flight,"endStationId"),0.0,(int)seats,20.0,80.0,input.reason()),actor);
            db.update("UPDATE st_commute_flight SET task_id=?,revision=revision+1 WHERE id=?",taskId,id);
        }else if(action.equals("cancel")){
            if(taskId!=null){var task=db.one("SELECT status FROM st_task WHERE id=? FOR UPDATE",taskId);require(!Set.of("executing","completed").contains(s(task,"status")),"执行中或已完成班次不能取消");if(Set.of("created","assigned").contains(s(task,"status")))sky.taskAction(taskId,"cancel",new SkyInputs.Action(null,input.reason()),actor);}
            db.update("UPDATE st_commute_booking SET status='cancelled',cancelled_time=NOW(3) WHERE flight_id=? AND status='confirmed'",id);
            db.update("UPDATE st_commute_flight SET status='cancelled',revision=revision+1,reason=? WHERE id=?",input.reason(),id);
        }else require(false,"班次动作无效");
        audit(db,id,"commute."+action,input.reason(),actor);return detail(id);
    }
}
