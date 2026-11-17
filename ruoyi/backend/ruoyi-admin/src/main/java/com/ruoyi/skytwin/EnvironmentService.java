package com.ruoyi.skytwin;

import java.nio.charset.StandardCharsets;
import java.time.*;
import java.util.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.common.exception.ServiceException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Evidence -> human review -> existing task engine -> evidence-backed human closure. */
@Service
public class EnvironmentService {
    private final SkyRepository db;private final SkyService sky;private final RouteService routes;private final ObjectMapper mapper;
    public EnvironmentService(SkyRepository db,SkyService sky,RouteService routes,ObjectMapper mapper) { this.db=db;this.sky=sky;this.routes=routes;this.mapper=mapper; }
    private static final String META="d.id,d.request_id,d.task_id,d.title,d.longitude,d.latitude,d.observed_at,d.image_source,d.analysis_source,d.image_mime,d.image_sha256,d.image_width,d.image_height,d.original_name,d.annotations_json,d.status,d.created_by,d.created_time,d.severity,d.event_id,d.reviewed_by,d.reviewed_at,d.review_reason,d.resolution,d.resolved_by,d.resolved_at,d.after_mime,d.after_sha256,d.after_width,d.after_height";
    private static String s(Map<String,Object> row,String key) { return Objects.toString(row.get(key),""); }
    private static void require(boolean ok,String message) { if(!ok) throw new ServiceException(message,409); }
    private static String id(String prefix) { return prefix+UUID.randomUUID().toString().replace("-",""); }
    private String json(Object value) {
        try { return mapper.writeValueAsString(value); } catch(Exception e) { throw new IllegalStateException("环境证据序列化失败",e); }
    }
    private Object parse(Object value) {
        try { return mapper.readValue(Objects.toString(value),Object.class); } catch(Exception e) { throw new IllegalStateException("环境证据读取失败",e); }
    }
    private Map<String,Object> discovery(String id,boolean locked) {
        var row=db.one("SELECT "+META+" FROM st_env_discovery d WHERE d.id=?"+(locked?" FOR UPDATE":""),id);
        row.put("annotations",parse(row.remove("annotationsJson")));return row;
    }
    private void audit(String id,String action,String reason,String actor) { db.update("INSERT INTO st_audit(entity_id,action,reason,actor) VALUES(?,?,?,?)",id,action,reason,actor); }
    @Transactional(readOnly=true)
    public List<Map<String,Object>> list(String status) {
        require(status==null || Set.of("pending_review","rejected","confirmed","in_response","closed").contains(status),"发现状态筛选无效");
        return db.rows("SELECT d.id,d.task_id,d.title,d.longitude,d.latitude,d.status,d.image_source,d.analysis_source,d.severity,d.event_id,d.created_by,d.created_time FROM st_env_discovery d"+(status==null?"":" WHERE d.status=?")+" ORDER BY d.created_time DESC,d.id DESC LIMIT 200",status==null?new Object[]{}:new Object[]{status});
    }
    private List<Map<String,Object>> responses(String id,boolean locked) {
        return db.rows("SELECT r.*,t.status task_status,t.title task_title,t.aircraft_id,t.progress,t.duration_seconds FROM st_env_response r JOIN st_task t ON t.id=r.task_id WHERE r.discovery_id=? ORDER BY r.attempt"+(locked?" FOR UPDATE":""),id);
    }
    @Transactional(readOnly=true)
    public Map<String,Object> detail(String id) {
        var result=discovery(id,false);
        var analyses=db.rows("SELECT id,model_name,model_sha256,result_json FROM st_env_analysis WHERE discovery_id=?",id);
        result.put("visionAnalysis",analyses.isEmpty()?null:analyses.get(0));
        if(!analyses.isEmpty())analyses.get(0).put("result",parse(analyses.get(0).remove("resultJson")));
        result.put("responses",responses(id,false));
        result.put("audit",db.rows("SELECT * FROM st_audit WHERE entity_id=? ORDER BY id",id));
        result.put("report",db.rows("SELECT id,created_by,created_time FROM st_env_report WHERE discovery_id=?",id).stream().findFirst().orElse(null));
        return result;
    }
    @Transactional
    public Map<String,Object> create(EnvironmentInputs.Discovery input,EnvironmentImage image,String actor) {
        try {
            EnvironmentRules.coordinate(input.longitude(),input.latitude());EnvironmentRules.observed(input.observedAt(),Instant.now());
            for(var b:input.annotations()) EnvironmentRules.box(b.x(),b.y(),b.width(),b.height());
        } catch(IllegalArgumentException e) { throw new ServiceException(e.getMessage(),400); }
        TrafficService.lock(db);
        String hash=EnvironmentImage.hash((json(input)+"\n"+image.sha256()).getBytes(StandardCharsets.UTF_8));
        var existing=db.rows("SELECT id,request_hash,created_by FROM st_env_discovery WHERE request_id=? FOR UPDATE",input.requestId());
        if(!existing.isEmpty()) {
            require(hash.equals(s(existing.get(0),"requestHash")) && actor.equals(s(existing.get(0),"createdBy")),"提交标识已用于其他内容，请重新提交");
            return detail(s(existing.get(0),"id"));
        }
        var source=db.one("SELECT * FROM st_task WHERE id=? FOR UPDATE",input.taskId());
        require("environment".equals(s(source,"type")) && Set.of("executing","completed").contains(s(source,"status")),"影像必须关联执行中或已完成的环境巡检任务");
        if(input.analysisId()!=null) {
            var analysis=db.one("SELECT * FROM st_env_analysis WHERE id=? FOR UPDATE",input.analysisId());
            VisionAnalysisService.validateLink(analysis,image,actor);
        }
        String id=id("ED-");
        db.update("INSERT INTO st_env_discovery(id,request_id,request_hash,task_id,title,longitude,latitude,observed_at,image_source,image_bytes,image_mime,image_sha256,image_width,image_height,original_name,annotations_json,created_by) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            id,input.requestId(),hash,input.taskId(),input.title().trim(),input.longitude(),input.latitude(),LocalDateTime.ofInstant(input.observedAt(),ZoneOffset.UTC),input.imageSource(),
            image.bytes(),image.mime(),image.sha256(),image.width(),image.height(),image.originalName(),json(input.annotations()),actor);
        if(input.analysisId()!=null) {
            db.update("UPDATE st_env_analysis SET discovery_id=? WHERE id=?",id,input.analysisId());
            db.update("UPDATE st_env_discovery SET analysis_source='model_assisted_manual_review' WHERE id=?",id);
        }
        audit(id,"environment.create",input.analysisId()==null?"上传河道漂浮物影像并人工标注（非AI识别）":"上传模型辅助发现，保留原始预测并等待人工复核",actor);return detail(id);
    }
    @Transactional
    public Map<String,Object> review(String id,EnvironmentInputs.Review input,String actor) {
        TrafficService.lock(db);var row=discovery(id,true);
        require("pending_review".equals(s(row,"status")),"该发现已经复核，不能重复生成事件");
        Long event=null;
        if("confirm".equals(input.decision())) {
            var task=db.one("SELECT * FROM st_task WHERE id=? FOR SHARE",row.get("taskId"));
            db.update("INSERT INTO st_event(task_id,aircraft_id,severity,title) VALUES(?,?,?,?)",row.get("taskId"),task.get("aircraftId"),input.severity(),"河道漂浮物："+s(row,"title"));
            event=db.count("SELECT LAST_INSERT_ID()");
        }
        db.update("UPDATE st_env_discovery SET status=?,severity=?,event_id=?,reviewed_by=?,reviewed_at=NOW(3),review_reason=? WHERE id=?",
            event==null?"rejected":"confirmed",input.severity(),event,actor,input.reason(),id);
        audit(id,"environment.review",input.reason(),actor);return detail(id);
    }
    @Transactional
    public Map<String,Object> respond(String id,EnvironmentInputs.Response input,String actor) {
        TrafficService.lock(db);var row=discovery(id,true);
        require(Set.of("confirmed","in_response").contains(s(row,"status")),"只有已确认且未结案事件可以安排应急侦察");
        var previous=responses(id,true);
        require(previous.stream().allMatch(r->Set.of("completed","cancelled","failed").contains(s(r,"taskStatus"))),"已有未结束的处置任务，请先执行或终止，不能重复占用资源");
        String task=sky.createTask(new SkyInputs.Task("环境侦察："+s(row,"title"),"rescue",input.startStationId(),input.endStationId(),0.0,0,10.0,80.0,input.reason()),actor);
        routes.save(task,new RouteInputs.Save(1,List.of(new RouteInputs.Waypoint(FlightRoutes.n(row,"longitude"),FlightRoutes.n(row,"latitude"))),input.reason()),actor);
        int priority=EnvironmentRules.priority(s(row,"severity"));
        db.update("INSERT INTO st_env_response(id,discovery_id,task_id,attempt,priority,reason,created_by) VALUES(?,?,?,?,?,?,?)",id("ER-"),id,task,previous.size()+1,priority,input.reason(),actor);
        db.update("UPDATE st_env_discovery SET status='in_response' WHERE id=?",id);
        audit(id,"environment.respond",input.reason(),actor);return detail(id);
    }
    @Transactional
    public Map<String,Object> close(String id,EnvironmentInputs.Close input,EnvironmentImage after,String actor) {
        TrafficService.lock(db);var row=discovery(id,true);
        require("in_response".equals(s(row,"status")),"只有完成应急侦察后的事件可以结案");
        var responses=responses(id,true);
        require(!responses.isEmpty() && responses.stream().noneMatch(r->Set.of("created","assigned","executing").contains(s(r,"taskStatus")))
            && "completed".equals(s(responses.get(responses.size()-1),"taskStatus")),"最新应急侦察必须完成，失败或取消不能当作处置成功");
        String latest=s(responses.get(responses.size()-1),"taskId");
        var tracks=db.rows("SELECT * FROM st_track WHERE task_id=? ORDER BY id",latest);
        require(tracks.stream().anyMatch(p->FlightRoutes.n(p,"altitude")>0 && EnvironmentRules.distance(FlightRoutes.n(row,"longitude"),FlightRoutes.n(row,"latitude"),FlightRoutes.n(p,"longitude"),FlightRoutes.n(p,"latitude"))<=10),"缺少事件点上空的服务端飞行轨迹，不能结案");
        require(!after.sha256().equals(row.get("imageSha256")),"处置后证据不能与发现图片完全相同");
        db.one("SELECT id FROM st_event WHERE id=? AND status='open' FOR UPDATE",row.get("eventId"));
        db.update("UPDATE st_env_discovery SET status='closed',resolution=?,resolved_by=?,resolved_at=NOW(3),after_bytes=?,after_mime=?,after_sha256=?,after_width=?,after_height=? WHERE id=?",
            input.resolution(),actor,after.bytes(),after.mime(),after.sha256(),after.width(),after.height(),id);
        db.update("UPDATE st_event SET status='resolved',resolution=?,resolved_by=?,resolved_time=NOW(3) WHERE id=?",input.resolution(),actor,row.get("eventId"));
        audit(id,"environment.close",input.resolution(),actor);
        var snapshot=detail(id);snapshot.put("latestResponseTracks",tracks);snapshot.put("latestResponseRoute",routes.detail(latest).get("plan"));snapshot.put("source","human_review_and_simulation");
        String content="河道漂浮物发现与应急处置归档（人工复核 / 本地仿真，非真实救援）\n发现："+s(row,"title")+"\n发现编号："+id+"\n巡检任务："+s(row,"taskId")
            +"\n位置（用户标注WGS84，未经定位设备验证）："+row.get("longitude")+", "+row.get("latitude")+"\n用户声明影像来源："+s(row,"imageSource")
            +"\n采集时间（UTC）："+s(row,"observedAt")+"Z\n标注来源："+s(row,"analysisSource")+"（人工提交框；原始模型预测见证据快照）\n标注框："+json(row.get("annotations"))
            +"\n复核人："+s(row,"reviewedBy")+"\n复核结论："+s(row,"reviewReason")+"\n事件等级："+s(row,"severity")+"\n应急侦察尝试："+responses.size()
            +"\n最新完成任务："+latest+"\n服务端轨迹点："+tracks.size()+"\n发现图片SHA-256："+s(row,"imageSha256")+"\n处置后图片SHA-256："+after.sha256()
            +"\n人工处置说明："+input.resolution()+"\n结案人："+actor+"\n结案时间："+s(snapshot,"resolvedAt")+"\n系统只证明软件流程与证据关联，不证明真实清理效果；无人机未在河面降落。";
        db.update("INSERT INTO st_env_report(id,discovery_id,content,snapshot_json,created_by) VALUES(?,?,?,?,?)",id("EP-"),id,content,json(snapshot),actor);
        return detail(id);
    }
    public Map<String,Object> image(String id,boolean after) {
        var result=db.one(after?"SELECT after_bytes image_bytes,after_mime image_mime FROM st_env_discovery WHERE id=? AND status='closed'":"SELECT image_bytes,image_mime FROM st_env_discovery WHERE id=?",id);
        return result;
    }
    public List<Map<String,Object>> reports() { return db.rows("SELECT r.id,r.discovery_id,d.title,r.created_by,r.created_time FROM st_env_report r JOIN st_env_discovery d ON d.id=r.discovery_id ORDER BY r.created_time DESC LIMIT 200"); }
    public Map<String,Object> report(String id) {
        var row=db.one("SELECT * FROM st_env_report WHERE id=?",id);row.put("snapshot",parse(row.remove("snapshotJson")));return row;
    }
}
