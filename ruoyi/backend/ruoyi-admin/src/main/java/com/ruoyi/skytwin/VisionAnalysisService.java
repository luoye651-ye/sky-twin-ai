package com.ruoyi.skytwin;

import com.fasterxml.jackson.databind.*;
import com.ruoyi.common.exception.ServiceException;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.TimeUnit;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

/** Fixed calculator, persistent evidence, no business state outside Java. */
@Service
public class VisionAnalysisService {
    private final SkyRepository db; private final ObjectMapper mapper; private final Path root; private final TransactionTemplate tx;
    private static final String META="id,status,created_by,created_time,ended_time,image_sha256,image_width,image_height,model_sha256,model_name,result_json,error_message,discovery_id";
    public VisionAnalysisService(SkyRepository db,ObjectMapper mapper,PlatformTransactionManager manager,@Value("${skytwin.ai-root:../ai}") String aiRoot) {
        this.db=db;this.mapper=mapper;this.tx=new TransactionTemplate(manager);this.root=Path.of(aiRoot).toAbsolutePath().normalize();
    }
    private static void require(boolean ok,String message) {if(!ok)throw new ServiceException(message,409);}
    private static String s(Map<String,Object> row,String key) {return Objects.toString(row.get(key),"");}
    @EventListener(ApplicationReadyEvent.class)
    public void recover() {db.update("UPDATE st_env_analysis SET status='failed',error_message='服务重启中断分析，请重新提交',ended_time=NOW(3) WHERE status='running'");}
    public Map<String,Object> detail(String id) {
        var row=db.one("SELECT "+META+" FROM st_env_analysis WHERE id=?",id);
        var text=row.remove("resultJson");
        try{row.put("result",text==null?null:mapper.readTree(text.toString()));}catch(Exception e){throw new ServiceException("分析结果读取失败",500);}
        return row;
    }
    public Map<String,Object> image(String id) {
        return db.one("SELECT image_bytes,image_mime FROM st_env_analysis WHERE id=?",id);
    }
    public Map<String,Object> analyze(String requestId,EnvironmentImage image,String actor) {
        try{require(UUID.fromString(requestId).toString().equals(requestId),"请求编号无效");}catch(IllegalArgumentException e){throw new ServiceException("请求编号无效",400);}
        final JsonNode config;
        try{
            Path cfg=root.resolve("weights/patrol/model.json");require(Files.size(cfg)<100_000,"模型配置异常");
            config=mapper.readTree(Files.readString(cfg));
            require(config.path("modelSha256").asText().matches("[a-f0-9]{64}"),"模型版本无效");
        }catch(java.io.IOException e){throw new ServiceException("已发布模型尚未就绪",409);}
        boolean[] created={false};
        String id=tx.execute(status->{
            TrafficService.lock(db);
            var existing=db.rows("SELECT * FROM st_env_analysis WHERE request_id=? FOR UPDATE",requestId);
            if(!existing.isEmpty()) {
                var row=existing.get(0);require(actor.equals(s(row,"createdBy")) && image.sha256().equals(s(row,"imageSha256")),"请求编号已用于其他影像或账号");return s(row,"id");
            }
            require(db.count("SELECT COUNT(*) FROM st_env_analysis WHERE status='running'")==0,"已有影像正在分析，请稍后重试");
            String key=UUID.randomUUID().toString();
            db.update("INSERT INTO st_env_analysis(id,request_id,status,created_by,image_bytes,image_mime,image_sha256,image_width,image_height,model_sha256,model_name) VALUES(?,?,'running',?,?,?,?,?,?,?,?)",
                key,requestId,actor,image.bytes(),image.mime(),image.sha256(),image.width(),image.height(),config.path("modelSha256").asText(),config.path("modelName").asText());
            created[0]=true;return key;
        });
        if(!created[0])return detail(id);
        Process process=null;
        try{
            var output=root.resolve("runs/vision/"+id);Files.createDirectories(output);Files.write(output.resolve("input.image"),image.bytes());
            var log=root.resolve("logs/vision");Files.createDirectories(log);
            process=new ProcessBuilder(root.resolve(".venv/Scripts/python.exe").toString(),root.resolve("scripts/vision_upload.py").toString(),
                "--id",id,"--model-sha",config.path("modelSha256").asText(),"--image-sha",image.sha256()).directory(root.toFile())
                .redirectErrorStream(true).redirectOutput(log.resolve(id+".log").toFile()).start();
            require(process.waitFor(120,TimeUnit.SECONDS),"影像分析超时");require(process.exitValue()==0,"影像分析失败，请检查计算日志；未创建事件");
            var file=output.resolve("result.json");require(Files.size(file)<100_000,"分析结果过大");var result=mapper.readTree(Files.readString(file));
            validateResult(result,id,image,config.path("modelSha256").asText());
            db.update("UPDATE st_env_analysis SET status='completed',result_json=?,ended_time=NOW(3) WHERE id=? AND status='running'",mapper.writeValueAsString(result),id);
        }catch(Exception e){
            db.update("UPDATE st_env_analysis SET status='failed',error_message=?,ended_time=NOW(3) WHERE id=? AND status='running'",
                e instanceof ServiceException?e.getMessage():"模型分析未完成，请检查运行环境；未创建事件",id);
            if(e instanceof InterruptedException)Thread.currentThread().interrupt();
        }finally{if(process!=null && process.isAlive())process.destroyForcibly();}
        return detail(id);
    }
    static void validateLink(Map<String,Object> analysis,EnvironmentImage image,String actor) {
        require("completed".equals(s(analysis,"status")) && actor.equals(s(analysis,"createdBy"))
            && image.sha256().equals(s(analysis,"imageSha256")) && analysis.get("discoveryId")==null,
            "分析未完成、影像不匹配、不是本人分析或该分析已关联发现");
    }
    static void validateResult(JsonNode result,String id,EnvironmentImage image,String model) {
        require(id.equals(result.path("analysisId").asText()) && image.sha256().equals(result.path("imageSha256").asText()) && model.equals(result.path("modelSha256").asText()),"分析证据指纹不一致");
        require(result.path("width").asInt()==image.width() && result.path("height").asInt()==image.height() && result.path("confidenceThreshold").asDouble()==.25,"分析图像或阈值不一致");
        var predictions=result.path("predictions");require(predictions.isArray() && predictions.size()<=100,"检测框数量异常");
        for(var box:predictions){
            for(String key:List.of("x","y","width","height","confidence"))require(box.path(key).isNumber() && Double.isFinite(box.path(key).asDouble()),"检测框数值异常");
            try{EnvironmentRules.box(box.path("x").asDouble(),box.path("y").asDouble(),box.path("width").asDouble(),box.path("height").asDouble());}catch(IllegalArgumentException e){throw new ServiceException("检测框越界",409);}
            require(Set.of("garbage","bottle").contains(box.path("label").asText()) && box.path("confidence").asDouble()>=.25 && box.path("confidence").asDouble()<=1,"检测类别或置信度异常");
        }
    }
}
