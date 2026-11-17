package com.ruoyi.skytwin;

import java.time.*;
import java.util.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import com.ruoyi.common.exception.ServiceException;

@Service
public class PositionService {
    private final SkyRepository db;
    public PositionService(SkyRepository db) { this.db=db; }
    private static void require(boolean ok,String message) { if(!ok) throw new ServiceException(message,409); }
    private static String s(Map<String,Object> row,String key) { return Objects.toString(row.get(key),""); }
    private static double n(Map<String,Object> row,String key) { return ((Number)row.get(key)).doubleValue(); }
    private static boolean flag(Map<String,Object> row,String key) { return row.get(key) instanceof Boolean b?b: n(row,key)!=0; }
    private static LocalDateTime utc(Instant value) { return LocalDateTime.ofInstant(value,ZoneOffset.UTC); }
    private static Instant instant(Map<String,Object> row,String key) { return LocalDateTime.parse(s(row,key)).toInstant(ZoneOffset.UTC); }
    private static PositionRules.Point point(Map<String,Object> row) { return new PositionRules.Point(instant(row,"sampledAt"),n(row,"longitude"),n(row,"latitude"),n(row,"altitude")); }
    private static void timestamps(Map<String,Object> row) {
        for(String key:List.of("sampledAt","receivedAt","enabledAt")) if(row.get(key)!=null) row.put(key,instant(row,key).toString());
        for(String key:List.of("accepted","fixValid","enabled")) if(row.containsKey(key)) row.put(key,flag(row,key));
    }
    private void audit(String id,String action,String reason,String actor) { db.update("INSERT INTO st_audit(entity_id,action,reason,actor) VALUES(?,?,?,?)",id,action,reason,actor); }
    public static void assertSimulationAvailable(SkyRepository db,String aircraftId) {
        // Call only while holding the aircraft row lock, shared with enable/disable.
        require(db.rows("SELECT id FROM st_position_device WHERE aircraft_id=? AND enabled=1 FOR SHARE",aircraftId).isEmpty(),
            "该飞行器已启用终端定位，请先停用终端定位再维护资源或派发仿真任务");
    }
    @Transactional
    public String create(PositionInputs.Device input,String actor) {
        db.one("SELECT id FROM st_aircraft WHERE id=? AND deleted=0 FOR UPDATE",input.aircraftId());
        require(db.count("SELECT COUNT(*) FROM st_position_device WHERE id=? OR aircraft_id=?",input.id(),input.aircraftId())==0,"终端编号或飞行器已绑定；第一版绑定关系不可修改");
        db.update("INSERT INTO st_position_device(id,name,aircraft_id,created_by) VALUES(?,?,?,?)",input.id(),input.name(),input.aircraftId(),actor);
        audit(input.id(),"position.bind","绑定仿真定位终端",actor);return input.id();
    }
    @Transactional
    public Map<String,Object> mode(String id,PositionInputs.Mode input,String actor) {
        var binding=db.one("SELECT aircraft_id FROM st_position_device WHERE id=?",id);
        var aircraft=db.one("SELECT * FROM st_aircraft WHERE id=? AND deleted=0 FOR UPDATE",binding.get("aircraftId"));
        var device=db.one("SELECT * FROM st_position_device WHERE id=? FOR UPDATE",id);
        require(!input.enabled() || "idle".equals(s(aircraft,"status")),"仅空闲飞行器可启用终端定位");
        if(flag(device,"enabled")!=input.enabled()) {
            if(input.enabled()) db.update("UPDATE st_position_device SET enabled=1,session_id=?,last_sequence=-1,latest_sample_id=NULL,enabled_at=? WHERE id=?",UUID.randomUUID().toString(),utc(Instant.now()),id);
            else db.update("UPDATE st_position_device SET enabled=0 WHERE id=?",id);
            audit(id,input.enabled()?"position.enable":"position.disable",input.reason(),actor);
        }
        return devices().stream().filter(x->id.equals(x.get("id"))).findFirst().orElseThrow();
    }
    public List<Map<String,Object>> devices() {
        var rows=db.rows("SELECT d.*,a.name aircraft_name,p.sampled_at,p.received_at,p.longitude,p.latitude,p.altitude FROM st_position_device d JOIN st_aircraft a ON a.id=d.aircraft_id LEFT JOIN st_position_sample p ON p.id=d.latest_sample_id ORDER BY d.created_time,d.id");
        Instant now=Instant.now();
        for(var row:rows) {
            String state="disabled";
            if(flag(row,"enabled")) {
                Instant reference=row.get("sampledAt")==null?instant(row,"enabledAt"):instant(row,"sampledAt");
                long age=Math.max(0,Duration.between(reference,now).toMillis());
                state=age>30000?"offline":row.get("sampledAt")==null?"waiting":age>5000?"stale":"online";
            }
            row.put("connectionState",state);row.put("serverTime",now.toString());timestamps(row);
        }
        return rows;
    }
    @Transactional
    public Map<String,Object> ingest(String id,PositionInputs.Sample input) {
        Instant sampled;
        try { sampled=PositionRules.time(input.sampledAt()); }
        catch(RuntimeException e) { throw new ServiceException("采样时间须为带时区的 ISO 时间，最多保留毫秒",400); }
        var device=db.one("SELECT * FROM st_position_device WHERE id=? FOR UPDATE",id);
        require(flag(device,"enabled") && input.sessionId().equals(s(device,"sessionId")),"终端未启用或会话已失效，请刷新终端状态");
        var previousReceipt=db.rows("SELECT * FROM st_position_sample WHERE device_id=? AND session_id=? AND sequence_no=?",id,input.sessionId(),input.sequence());
        if(!previousReceipt.isEmpty()) {
            var row=previousReceipt.get(0);
            require(instant(row,"sampledAt").equals(sampled) && n(row,"longitude")==input.longitude() && n(row,"latitude")==input.latitude()
                && n(row,"altitude")==input.altitude() && flag(row,"fixValid")==input.fixValid(),"同一会话序号内容冲突");
            timestamps(row);row.put("duplicate",true);return row;
        }
        var previous=device.get("latestSampleId")==null?null:db.one("SELECT * FROM st_position_sample WHERE id=?",device.get("latestSampleId"));
        Instant received=Instant.now().truncatedTo(java.time.temporal.ChronoUnit.MILLIS);
        String verdict=PositionRules.verdict(new PositionRules.Point(sampled,input.longitude(),input.latitude(),input.altitude()),received,input.sequence(),((Number)device.get("lastSequence")).longValue(),input.fixValid(),previous==null?null:point(previous));
        boolean accepted="accepted".equals(verdict);
        db.update("INSERT INTO st_position_sample(device_id,session_id,sequence_no,sampled_at,received_at,longitude,latitude,altitude,fix_valid,accepted,verdict) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            id,input.sessionId(),input.sequence(),utc(sampled),utc(received),input.longitude(),input.latitude(),input.altitude(),input.fixValid(),accepted,verdict);
        var result=db.one("SELECT * FROM st_position_sample WHERE device_id=? AND session_id=? AND sequence_no=?",id,input.sessionId(),input.sequence());
        db.update("UPDATE st_position_device SET last_sequence=GREATEST(last_sequence,?),latest_sample_id=? WHERE id=?",input.sequence(),accepted?result.get("id"):device.get("latestSampleId"),id);
        timestamps(result);result.put("duplicate",false);return result;
    }
    public Map<String,Object> samples(String id,String from,String to,long after,int limit,boolean acceptedOnly) {
        db.one("SELECT id FROM st_position_device WHERE id=?",id);
        require(after>=0 && limit>=1 && limit<=1000,"分页参数超出范围");
        Instant begin,end;
        try { begin=PositionRules.time(from);end=PositionRules.time(to); }
        catch(RuntimeException e) { throw new ServiceException("查询时间须为带时区的 ISO 时间",400); }
        require(begin.isBefore(end) && Duration.between(begin,end).compareTo(Duration.ofDays(7))<=0,"查询时段须大于0且不超过7天");
        // Cursor uses ingestion ID, not sampledAt: rejected out-of-order times must not break pagination.
        var rows=db.rows("SELECT * FROM st_position_sample WHERE device_id=? AND sampled_at>=? AND sampled_at<? AND id>?"+(acceptedOnly?" AND accepted=1":"")+" ORDER BY id LIMIT ?",id,utc(begin),utc(end),after,limit+1);
        boolean more=rows.size()>limit;
        if(more) rows=new ArrayList<>(rows.subList(0,limit));
        rows.forEach(PositionService::timestamps);
        long cursor=rows.isEmpty()?after:((Number)rows.get(rows.size()-1).get("id")).longValue();
        return Map.of("rows",rows,"hasMore",more,"nextCursor",cursor,"serverTime",Instant.now().toString());
    }
    public List<Map<String,Object>> recent(String id) {
        db.one("SELECT id FROM st_position_device WHERE id=?",id);
        var rows=db.rows("SELECT * FROM st_position_sample WHERE device_id=? ORDER BY id DESC LIMIT 100",id);
        rows.forEach(PositionService::timestamps);return rows;
    }
    public List<Map<String,Object>> overlay(List<Map<String,Object>> aircraft) {
        var active=devices().stream().filter(x->flag(x,"enabled")).toList();
        for(var a:aircraft) for(var d:active) if(a.get("id").equals(d.get("aircraftId"))) {
            a.put("positionSource","simulated_terminal");a.put("positionState",d.get("connectionState"));a.put("positionDeviceId",d.get("id"));a.put("positionSampledAt",d.get("sampledAt"));
            if(d.get("sampledAt")!=null) for(String key:List.of("longitude","latitude","altitude")) a.put(key,d.get(key));
        }
        return aircraft;
    }
}
