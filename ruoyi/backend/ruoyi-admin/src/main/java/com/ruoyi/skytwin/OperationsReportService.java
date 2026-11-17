package com.ruoyi.skytwin;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.charset.StandardCharsets;
import java.util.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import static com.ruoyi.skytwin.OperationsRules.*;

@Service
public class OperationsReportService {
    private final SkyRepository db;private final EnvironmentService environment;private final ObjectMapper mapper;
    public OperationsReportService(SkyRepository db,EnvironmentService environment,ObjectMapper mapper){this.db=db;this.environment=environment;this.mapper=mapper;}
    private String json(Object value){try{return mapper.writeValueAsString(value);}catch(Exception e){throw new IllegalStateException(e);}}
    private Map<String,Object> facts(String kind,String id){
        if(kind.equals("discovery"))return environment.detail(id);
        require(kind.equals("task"),"报告来源无效");
        var row=db.one("SELECT t.*,s.name start_station_name,e.name end_station_name,a.name aircraft_name FROM st_task t JOIN st_station s ON s.id=t.start_station_id JOIN st_station e ON e.id=t.end_station_id LEFT JOIN st_aircraft a ON a.id=t.aircraft_id WHERE t.id=?",id);
        row.put("trackCount",db.count("SELECT COUNT(*) FROM st_track WHERE task_id=?",id));row.put("events",db.rows("SELECT id,title,status,severity,resolution FROM st_event WHERE task_id=? ORDER BY id",id));return row;
    }
    public Map<String,Object> list(int page,int size){return page(db,"SELECT r.*,v.source ","FROM st_ops_report r JOIN st_ops_report_version v ON v.report_id=r.id AND v.revision=r.revision","",List.of(),page,size," ORDER BY r.created_time DESC,r.id DESC");}
    public Map<String,Object> detail(String id){var row=db.one("SELECT r.*,v.content,v.source FROM st_ops_report r JOIN st_ops_report_version v ON v.report_id=r.id AND v.revision=r.revision WHERE r.id=?",id);try{row.put("snapshot",mapper.readTree(s(row,"snapshotJson")));}catch(Exception e){throw new IllegalStateException(e);}row.remove("snapshotJson");row.put("versions",db.rows("SELECT revision,source,created_by,created_time FROM st_ops_report_version WHERE report_id=? ORDER BY revision DESC",id));return row;}
    public Map<String,Object> version(String id,int revision){return db.one("SELECT * FROM st_ops_report_version WHERE report_id=? AND revision=?",id,revision);}
    @Transactional public Map<String,Object> create(OperationsInputs.Report input,String actor){
        uuid(input.requestId());TrafficService.lock(db);var prior=db.rows("SELECT * FROM st_ops_report WHERE request_id=? FOR UPDATE",input.requestId());
        if(!prior.isEmpty()){var row=prior.get(0);require(actor.equals(s(row,"createdBy"))&&input.sourceId().equals(s(row,"sourceId"))&&input.sourceKind().equals(s(row,"sourceKind")),"请求编号已用于其他报告");return detail(s(row,"id"));}
        var facts=facts(input.sourceKind(),input.sourceId());String snapshot=json(facts),hash=EnvironmentImage.hash(snapshot.getBytes(StandardCharsets.UTF_8)),id=id("OR-");String title=s(facts,"title")+" · 业务报告";
        String content=title+"\n\n来源编号："+input.sourceId()+"\n当前状态："+s(facts,"status")+"\n来源类型："+input.sourceKind()
            +(input.sourceKind().equals("task")?"\n起点："+s(facts,"startStationName")+"\n终点："+s(facts,"endStationName")+"\n飞行器："+s(facts,"aircraftName")+"\n进度："+facts.get("progress")+"%\n轨迹点："+facts.get("trackCount"):
            "\n人工声明位置："+facts.get("longitude")+", "+facts.get("latitude")+"\n分析来源："+s(facts,"analysisSource")+"\n复核结论："+s(facts,"reviewReason")+"\n处置说明："+s(facts,"resolution"))
            +"\n\n证据指纹："+hash+"\n此稿来自系统证据快照，需审核。飞行为本地仿真；图片来源/坐标为用户声明，不证明实机飞行或现实清理效果。";
        db.update("INSERT INTO st_ops_report(id,request_id,source_kind,source_id,title,snapshot_json,snapshot_sha256,created_by) VALUES(?,?,?,?,?,?,?,?)",id,input.requestId(),input.sourceKind(),input.sourceId(),title,snapshot,hash,actor);
        db.update("INSERT INTO st_ops_report_version(report_id,revision,content,source,created_by) VALUES(?,1,?,'manual',?)",id,content,actor);audit(db,id,"ops-report.create","创建证据快照草稿",actor);return detail(id);
    }
    @Transactional public Map<String,Object> edit(String id,OperationsInputs.ReportEdit input,String actor){
        TrafficService.lock(db);var row=db.one("SELECT * FROM st_ops_report WHERE id=? FOR UPDATE",id);
        require("draft".equals(s(row,"status")),"已审核报告不可修改，请另建新报告");require((int)n(row,"revision")==input.expectedRevision(),"报告版本已变化，请刷新后编辑");
        if(input.publish())require(s(row,"snapshotSha256").equals(EnvironmentImage.hash(json(facts(s(row,"sourceKind"),s(row,"sourceId"))).getBytes(StandardCharsets.UTF_8))),"业务证据已变化，请重新生成快照后再审核");
        int revision=input.expectedRevision()+1;db.update("INSERT INTO st_ops_report_version(report_id,revision,content,source,created_by) VALUES(?,?,?,?,?)",id,revision,input.content(),input.source(),actor);
        db.update("UPDATE st_ops_report SET revision=?,status=? WHERE id=?",revision,input.publish()?"reviewed":"draft",id);audit(db,id,"ops-report.save",input.publish()?"人工审核冻结报告":"保存报告草稿版本",actor);return detail(id);
    }
}
