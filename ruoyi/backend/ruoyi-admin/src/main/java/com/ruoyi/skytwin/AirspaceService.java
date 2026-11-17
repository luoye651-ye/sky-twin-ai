package com.ruoyi.skytwin;

import java.time.LocalDateTime;
import java.util.*;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.common.exception.ServiceException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AirspaceService {
    private final SkyRepository db;private final AirspaceRecords records;private final ObjectMapper mapper;private final FlightRoutes routes;
    public AirspaceService(SkyRepository db,AirspaceRecords records,ObjectMapper mapper,FlightRoutes routes) { this.db=db;this.records=records;this.mapper=mapper;this.routes=routes; }
    private static String text(Map<String,Object> row,String key) { return Objects.toString(row.get(key),""); }
    private static double number(Map<String,Object> row,String key) { return ((Number)row.get(key)).doubleValue(); }
    private static boolean flag(Map<String,Object> row,String key) { return Boolean.TRUE.equals(row.get(key)) || row.get(key) instanceof Number n && n.intValue()!=0; }
    private static LocalDateTime date(Map<String,Object> row,String key) { return row.get(key)==null?null:LocalDateTime.parse(text(row,key)); }
    private static void require(boolean value,String reason) { if(!value) throw new ServiceException(reason,409); }
    public List<Map<String,Object>> zones() {
        var rows=db.rows("SELECT * FROM st_airspace_zone ORDER BY created_time DESC,id");var now=LocalDateTime.now();
        for(var row:rows) row.put("activeNow",flag(row,"enabled") && (date(row,"startsAt")==null || !now.isBefore(date(row,"startsAt"))) && (date(row,"endsAt")==null || now.isBefore(date(row,"endsAt"))));
        return rows;
    }
    public long revision() { return db.count("SELECT revision FROM st_airspace_policy WHERE id=1"); }
    private long lockPolicy() { return ((Number)db.one("SELECT revision FROM st_airspace_policy WHERE id=1 FOR UPDATE").get("revision")).longValue(); }
    @Transactional
    public String save(String id,AirspaceInputs.Zone input,String actor) {
        require(Double.isFinite(input.west()) && Double.isFinite(input.east()) && Double.isFinite(input.south()) && Double.isFinite(input.north())
            && Double.isFinite(input.minAltitude()) && Double.isFinite(input.maxAltitude()),"区域坐标与高度必须是有限数值");
        require(input.west()<input.east() && input.south()<input.north(),"西经度须小于东经度，南纬度须小于北纬度");
        require(input.east()-input.west()<=2 && input.north()-input.south()<=2,"单个区域跨度最多2度，请拆分配置");
        require(input.minAltitude()<=input.maxAltitude(),"高度下限不能大于上限");
        require(!"height_limit".equals(input.type()) || input.minAltitude()==0,"限高区的高度下限应为0");
        require(input.startsAt()==null || input.endsAt()==null || input.startsAt().isBefore(input.endsAt()),"结束时间必须晚于开始时间");
        lockPolicy();
        if(id==null) {
            require(db.count("SELECT COUNT(*) FROM st_airspace_zone")<500,"第一版最多配置500个区域");
            id="AZ-"+UUID.randomUUID().toString().replace("-","");
            db.update("INSERT INTO st_airspace_zone(id,name,type,west,south,east,north,min_altitude,max_altitude,starts_at,ends_at,enabled,created_by,updated_by,reason) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                id,input.name().trim(),input.type(),input.west(),input.south(),input.east(),input.north(),input.minAltitude(),input.maxAltitude(),input.startsAt(),input.endsAt(),input.enabled(),actor,actor,input.reason());
        } else {
            db.one("SELECT id FROM st_airspace_zone WHERE id=? FOR UPDATE",id);
            db.update("UPDATE st_airspace_zone SET name=?,type=?,west=?,south=?,east=?,north=?,min_altitude=?,max_altitude=?,starts_at=?,ends_at=?,enabled=?,updated_by=?,reason=?,updated_time=NOW(3) WHERE id=?",
                input.name().trim(),input.type(),input.west(),input.south(),input.east(),input.north(),input.minAltitude(),input.maxAltitude(),input.startsAt(),input.endsAt(),input.enabled(),actor,input.reason(),id);
        }
        db.update("UPDATE st_airspace_policy SET revision=revision+1 WHERE id=1");
        db.update("INSERT INTO st_audit(entity_id,action,reason,actor) VALUES(?,'airspace.zone.save',?,?)",id,input.reason(),actor);return id;
    }
    private List<AirspaceEngine.Zone> readZones(boolean locked) {
        return db.rows("SELECT * FROM st_airspace_zone WHERE enabled=1 ORDER BY id"+(locked?" FOR SHARE":"")).stream().map(row->
            new AirspaceEngine.Zone(text(row,"id"),text(row,"name"),text(row,"type"),number(row,"west"),number(row,"south"),number(row,"east"),number(row,"north"),
                number(row,"minAltitude"),number(row,"maxAltitude"),date(row,"startsAt"),date(row,"endsAt"),flag(row,"enabled"))).toList();
    }
    private AirspaceEngine.Check check(String id,LocalDateTime departure,long revision,boolean locked) {
        var task=routes.task(id,locked);
        return AirspaceEngine.checkPath(id,text(task,"title"),routes.current(id,locked).points(),readZones(locked),departure,revision,LocalDateTime.now());
    }
    public AirspaceEngine.Check inspect(String taskId,LocalDateTime departure) {
        return check(taskId,departure,revision(),false);
    }
    /** Caller owns a transaction. Freeze policy and use current locking reads for reservations. */
    public AirspaceEngine.Check inspectLockedAt(String taskId,LocalDateTime departure) {
        return check(taskId,departure,lockPolicy(),true);
    }
    public AirspaceEngine.Check inspectPath(String taskId,String title,List<AirspaceEngine.Point> path,boolean persist,String actor) {
        long revision=lockPolicy();var now=LocalDateTime.now();
        var result=AirspaceEngine.checkPath(taskId,title,path,readZones(true),now,revision,now);
        if(persist) records.save(result,"route_save",actor);
        return result;
    }
    @Transactional
    public AirspaceEngine.Check validate(AirspaceInputs.Validate input,String actor) {
        db.one("SELECT id FROM st_task WHERE id=? FOR UPDATE",input.taskId());
        long revision=lockPolicy();var now=LocalDateTime.now();var departure=input.departureAt()==null?now:input.departureAt();
        require(!departure.isBefore(now.minusSeconds(5)) && !departure.isAfter(now.plusDays(30)),"预计起飞时间应为现在至未来30天以内");
        var result=check(input.taskId(),departure,revision,true);
        records.save(result,"manual",actor);return result;
    }
    @Transactional
    public void assertAllowed(String taskId,String entry,String actor) {
        long revision=lockPolicy();var now=LocalDateTime.now();
        var result=check(taskId,now,revision,true);
        records.save(result,entry,actor);
        require(result.allowed(),String.join("；",result.violations().stream().map(AirspaceEngine.Violation::reason).distinct().toList()));
    }
    public List<Map<String,Object>> checks() { return db.rows("SELECT id,task_id,task_title,entry,allowed,rule_revision,departure_at,created_by,created_time FROM st_airspace_check ORDER BY created_time DESC,id DESC LIMIT 200"); }
    public Map<String,Object> checkDetail(String id) {
        var row=db.one("SELECT * FROM st_airspace_check WHERE id=?",id);
        try { row.put("result",mapper.readValue(text(row,"detailsJson"),AirspaceEngine.Check.class));row.remove("detailsJson");return row; }
        catch(JsonProcessingException ex) { throw new IllegalStateException("空域记录读取失败",ex); }
    }
}
