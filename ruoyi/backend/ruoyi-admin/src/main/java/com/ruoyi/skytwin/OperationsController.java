package com.ruoyi.skytwin;
import java.util.*;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.http.*;
import org.springframework.web.util.HtmlUtils;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import static com.ruoyi.skytwin.OperationsRules.*;

@RestController @RequestMapping("/sky/operations")
public class OperationsController extends BaseController {
    private final SkyRepository db;private final TaskOperationsService tasks;private final ResourceOperationsService resources;private final CommuteService commute;private final OperationsReportService reports;private final VisionAnalysisService vision;
    public OperationsController(SkyRepository db,TaskOperationsService tasks,ResourceOperationsService resources,CommuteService commute,OperationsReportService reports,VisionAnalysisService vision){this.db=db;this.tasks=tasks;this.resources=resources;this.commute=commute;this.reports=reports;this.vision=vision;}
    @GetMapping("/spatial/tasks") @PreAuthorize("@ss.hasPermi('sky:read')")
    public AjaxResult spatial(@RequestParam double minLon,@RequestParam double maxLon,@RequestParam double minLat,@RequestParam double maxLat) {
        require(Double.isFinite(minLon)&&Double.isFinite(maxLon)&&Double.isFinite(minLat)&&Double.isFinite(maxLat)&&minLon>=-180&&maxLon<=180&&minLat>=-90&&maxLat<=90&&minLon<maxLon&&minLat<maxLat,"框选坐标范围无效");
        String from="FROM st_task t JOIN st_station s ON s.id=t.start_station_id JOIN st_station e ON e.id=t.end_station_id";
        String where=" WHERE t.status='created' AND ((s.longitude BETWEEN ? AND ? AND s.latitude BETWEEN ? AND ?) OR (e.longitude BETWEEN ? AND ? AND e.latitude BETWEEN ? AND ?))";
        return success(page(db,"SELECT t.id,t.title,t.status,s.name start_station_name,e.name end_station_name ",from,where,List.of(minLon,maxLon,minLat,maxLat,minLon,maxLon,minLat,maxLat),1,100," ORDER BY t.created_time DESC,t.id DESC"));
    }
    @GetMapping("/tasks") @PreAuthorize("@ss.hasPermi('sky:read')") public AjaxResult tasks(@RequestParam(defaultValue="1") int page,@RequestParam(defaultValue="20") int size,@RequestParam(defaultValue="") String state,@RequestParam(defaultValue="") String type,@RequestParam(defaultValue="") String keyword){return success(tasks.tasks(page,size,state,type,keyword));}
    @PostMapping("/tasks/{id}/retry") @PreAuthorize("@ss.hasPermi('sky:operate')") public AjaxResult retry(@PathVariable String id,@Valid @RequestBody OperationsInputs.Retry input){return success(tasks.retry(id,input,getUsername()));}
    @GetMapping("/resources") @PreAuthorize("@ss.hasPermi('sky:read')") public AjaxResult resources(@RequestParam(defaultValue="1") int page,@RequestParam(defaultValue="20") int size){return success(resources.history(page,size));}
    @PostMapping("/resources") @PreAuthorize("@ss.hasPermi('sky:manage')") public AjaxResult resource(@Valid @RequestBody OperationsInputs.Resource input){return success(resources.start(input,getUsername()));}
    @PostMapping("/resources/{id}/close") @PreAuthorize("@ss.hasPermi('sky:manage')") public AjaxResult close(@PathVariable String id,@Valid @RequestBody OperationsInputs.Close input){return success(resources.close(id,input,getUsername()));}
    @GetMapping("/stations") @PreAuthorize("@ss.hasPermi('sky:read')") public AjaxResult stations(){return success(resources.stations());}
    @PutMapping("/stations/{id}/capacity") @PreAuthorize("@ss.hasPermi('sky:manage')") public AjaxResult capacity(@PathVariable String id,@Valid @RequestBody OperationsInputs.Capacity input){resources.capacity(id,input,getUsername());return success();}
    @GetMapping("/flights") @PreAuthorize("@ss.hasPermi('sky:read')") public AjaxResult flights(@RequestParam(defaultValue="1") int page,@RequestParam(defaultValue="20") int size){return success(commute.list(page,size));}
    @GetMapping("/flights/{id}") @PreAuthorize("@ss.hasPermi('sky:read')") public AjaxResult flight(@PathVariable String id){return success(commute.detail(id));}
    @PostMapping("/flights") @PreAuthorize("@ss.hasPermi('sky:operate')") public AjaxResult createFlight(@Valid @RequestBody OperationsInputs.Flight input){return success(commute.create(input,getUsername()));}
    @PostMapping("/flights/{id}/{action:delay|activate|cancel}") @PreAuthorize("@ss.hasPermi('sky:operate')") public AjaxResult flightAction(@PathVariable String id,@PathVariable String action,@Valid @RequestBody OperationsInputs.FlightAction input){return success(commute.action(id,action,input,getUsername()));}
    @PostMapping("/flights/{id}/bookings") @PreAuthorize("@ss.hasPermi('sky:operate')") public AjaxResult book(@PathVariable String id,@Valid @RequestBody OperationsInputs.Booking input){return success(commute.book(id,input,getUsername()));}
    @PostMapping("/bookings/{id}/cancel") @PreAuthorize("@ss.hasPermi('sky:operate')") public AjaxResult cancelBooking(@PathVariable String id){commute.cancelBooking(id,getUsername());return success();}
    @GetMapping("/analyses") @PreAuthorize("@ss.hasPermi('sky:read')") public AjaxResult analyses(@RequestParam(defaultValue="1") int page,@RequestParam(defaultValue="20") int size,@RequestParam(defaultValue="") String state){
        return success(page(db,"SELECT id,status,created_by,created_time,ended_time,image_sha256,model_name,model_sha256,error_message,discovery_id ","FROM st_env_analysis",state.isBlank()?"":" WHERE status=?",state.isBlank()?List.of():List.of(state),page,size," ORDER BY created_time DESC,id DESC"));
    }
    @PostMapping("/analyses/{id}/retry") @PreAuthorize("@ss.hasPermi('sky:operate')") public AjaxResult retryAnalysis(@PathVariable String id,@RequestParam String requestId){
        var row=db.one("SELECT * FROM st_env_analysis WHERE id=?",id);require("failed".equals(s(row,"status"))&&getUsername().equals(s(row,"createdBy")),"只能重试本人失败的分析");
        var result=vision.analyze(requestId,EnvironmentImage.read((byte[])row.get("imageBytes"),"analysis-retry"),getUsername());audit(db,s(result,"id"),"vision.retry","重试原分析："+id,getUsername());return success(result);
    }
    @GetMapping("/reports") @PreAuthorize("@ss.hasPermi('sky:read')") public AjaxResult reports(@RequestParam(defaultValue="1") int page,@RequestParam(defaultValue="20") int size){return success(reports.list(page,size));}
    @GetMapping("/reports/{id}") @PreAuthorize("@ss.hasPermi('sky:read')") public AjaxResult report(@PathVariable String id){return success(reports.detail(id));}
    @GetMapping("/reports/{id}/versions/{revision}") @PreAuthorize("@ss.hasPermi('sky:read')") public AjaxResult reportVersion(@PathVariable String id,@PathVariable int revision){return success(reports.version(id,revision));}
    @PostMapping("/reports") @PreAuthorize("@ss.hasPermi('sky:operate')") public AjaxResult createReport(@Valid @RequestBody OperationsInputs.Report input){return success(reports.create(input,getUsername()));}
    @PutMapping("/reports/{id}") @PreAuthorize("@ss.hasPermi('sky:operate')") public AjaxResult editReport(@PathVariable String id,@Valid @RequestBody OperationsInputs.ReportEdit input){return success(reports.edit(id,input,getUsername()));}
    @GetMapping("/reports/{id}/export") @PreAuthorize("@ss.hasPermi('sky:read')") public ResponseEntity<String> export(@PathVariable String id,@RequestParam(defaultValue="txt") String format){
        require(Set.of("txt","html").contains(format),"导出格式无效");var row=reports.detail(id);String content=s(row,"content");
        boolean html=format.equals("html");if(html)content="<!doctype html><html lang=zh-CN><meta charset=utf-8><title>SkyTwin 报告</title><style>@page{size:A4;margin:20mm}body{font:14px/1.8 sans-serif;color:#111}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>"+HtmlUtils.htmlEscape(s(row,"title"))+"</h1><p>报告 "+HtmlUtils.htmlEscape(id)+" · 版本 "+row.get("revision")+" · "+HtmlUtils.htmlEscape(s(row,"status"))+"</p><pre>"+HtmlUtils.htmlEscape(content)+"</pre></html>";
        return ResponseEntity.ok().contentType(MediaType.parseMediaType(html?"text/html;charset=UTF-8":"text/plain;charset=UTF-8")).cacheControl(CacheControl.noStore()).header("X-Content-Type-Options","nosniff").header("Content-Disposition","attachment; filename=\""+id.replaceAll("[^A-Za-z0-9-]","")+"."+format+"\"").body(content);
    }
    @GetMapping("/query") @PreAuthorize("@ss.hasPermi('sky:read')") public AjaxResult query(@RequestParam String kind,@RequestParam(defaultValue="") String state,@RequestParam(defaultValue="") String keyword,@RequestParam(defaultValue="1") int page){
        require(keyword.length()<=200,"查询文字过长");
        if(kind.equals("tasks"))return success(tasks.tasks(page,20,state,"",keyword));
        if(kind.equals("reports")) {
            var reportArgs=new ArrayList<Object>();String where=" WHERE 1=1";
            if(!state.isBlank()){where+=" AND r.status=?";reportArgs.add(state);}
            if(!keyword.isBlank()){where+=" AND (r.id=? OR r.source_id=? OR r.title LIKE ?)";reportArgs.add(keyword);reportArgs.add(keyword);reportArgs.add("%"+keyword+"%");}
            return success(page(db,"SELECT r.id,r.title,r.status,r.revision,r.source_kind,r.source_id,r.created_time ","FROM st_ops_report r",where,reportArgs,page,20," ORDER BY r.created_time DESC,r.id DESC"));
        }
        require(kind.equals("events"),"查询类型仅支持tasks/events/reports");var args=new ArrayList<Object>();String where=" WHERE 1=1";
        if(!state.isBlank()){where+=" AND e.status=?";args.add(state);}if(!keyword.isBlank()){where+=" AND (e.title LIKE ? OR CAST(e.id AS CHAR)=? OR e.task_id=?)";args.add("%"+keyword+"%");args.add(keyword);args.add(keyword);}
        return success(page(db,"SELECT e.*,d.id discovery_id ","FROM st_event e LEFT JOIN st_env_discovery d ON d.event_id=e.id",where,args,page,20," ORDER BY e.id DESC"));
    }
    @GetMapping("/records/{kind}/{id}") @PreAuthorize("@ss.hasPermi('sky:read')") public AjaxResult record(@PathVariable String kind,@PathVariable String id){
        if(kind.equals("report"))return success(reports.detail(id));
        if(kind.equals("task")){var task=db.one("SELECT * FROM st_task WHERE id=?",id);task.put("trackCount",db.count("SELECT COUNT(*) FROM st_track WHERE task_id=?",id));task.put("reports",db.rows("SELECT id,title,content FROM st_report WHERE task_id=?",id));return success(task);}
        require(kind.equals("event"),"记录类型无效");return success(db.one("SELECT e.*,d.id discovery_id,d.longitude,d.latitude FROM st_event e LEFT JOIN st_env_discovery d ON d.event_id=e.id WHERE e.id=?",id));
    }
}
