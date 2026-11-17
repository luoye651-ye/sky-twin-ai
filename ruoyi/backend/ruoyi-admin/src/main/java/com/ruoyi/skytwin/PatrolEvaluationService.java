package com.ruoyi.skytwin;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.common.exception.ServiceException;
import jakarta.annotation.PreDestroy;
import java.io.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicReference;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Java owns persistent run state. Python is a bounded, fixed-protocol calculator. */
@Service
public class PatrolEvaluationService {
    private static final Logger LOG=LoggerFactory.getLogger(PatrolEvaluationService.class);
    private static final String META="id,request_id,status,stage,processed,model_name,model_sha256,dataset_sha256,image_count,created_by,created_time,started_time,ended_time,error_message,report_sha256";
    private final SkyRepository db;
    private final ObjectMapper mapper;
    private final TransactionTemplate tx;
    private final Path root;
    private final ExecutorService executor=Executors.newSingleThreadExecutor(r -> {var t=new Thread(r,"patrol-evaluator");t.setDaemon(true);return t;});
    private final AtomicReference<Process> child=new AtomicReference<>();
    private volatile boolean stopping=false;
    public PatrolEvaluationService(SkyRepository db,ObjectMapper mapper,PlatformTransactionManager manager,
            @Value("${skytwin.ai-root:../ai}") String aiRoot) {
        this.db=db;this.mapper=mapper;this.tx=new TransactionTemplate(manager);this.root=Path.of(aiRoot).toAbsolutePath().normalize();
    }
    private static String s(Map<String,Object> row,String key) { return Objects.toString(row.get(key),""); }
    private static void require(boolean ok,String message) {if(!ok) throw new ServiceException(message,409);}
    private static void uuid(String id) {try {require(UUID.fromString(id).toString().equals(id),"运行标识无效");}catch(IllegalArgumentException e){throw new ServiceException("运行标识无效",400);}}
    private String hash(byte[] bytes) {
        try{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));}catch(Exception e){throw new IllegalStateException(e);}
    }
    private String hash(Path file) throws IOException {
        try(var in=Files.newInputStream(file)) {
            var md=MessageDigest.getInstance("SHA-256");byte[] buffer=new byte[65536];int read;
            while((read=in.read(buffer))!=-1)md.update(buffer,0,read);
            return HexFormat.of().formatHex(md.digest());
        }catch(java.security.NoSuchAlgorithmException e){throw new IllegalStateException(e);}
    }
    private JsonNode configuration() throws IOException {
        var file=root.resolve("weights/patrol/model.json");
        if(Files.size(file)>100_000)throw new IOException("Configuration too large");
        var value=mapper.readTree(Files.readString(file));
        if(!value.path("modelSha256").asText().matches("[a-f0-9]{64}") || !value.path("datasetSha256").asText().matches("[a-f0-9]{64}")
            || value.path("imageCount").asInt()!=132 || !"test".equals(value.path("split").asText()))throw new IOException("Invalid configuration");
        if(!Files.isRegularFile(root.resolve(".venv/Scripts/python.exe")) || !Files.isRegularFile(root.resolve("scripts/patrol_eval.py"))
            || !Files.isRegularFile(root.resolve("weights/patrol/"+value.path("modelSha256").asText()+".pt")))throw new IOException("Missing evaluation runtime");
        return value;
    }
    public Map<String,Object> config() {
        try {
            var cfg=configuration();var result=new LinkedHashMap<String,Object>();
            result.put("ready",true);result.put("modelName",cfg.path("modelName").asText());result.put("modelSha256",cfg.path("modelSha256").asText());
            result.put("datasetSha256",cfg.path("datasetSha256").asText());result.put("imageCount",132);result.put("confidence",.25);result.put("matchIou",.5);
            result.put("sampleMin",1);result.put("sampleMax",132);
            result.put("message","从132张影像池随机抽取1至132张；仅用于巡逻演示，不替代完整测试集评测");return result;
        }catch(IOException e){return Map.of("ready",false,"message","识别模型尚未发布：请等待训练完成并运行模型固定脚本；不会使用中间权重或伪造检测结果");}
    }
    public List<Map<String,Object>> list(){return db.rows("SELECT "+META+" FROM st_patrol_eval ORDER BY created_time DESC,id DESC LIMIT 30");}
    public Map<String,Object> detail(String id) {
        uuid(id);var result=db.one("SELECT "+META+",report_json FROM st_patrol_eval WHERE id=?",id);
        var text=result.remove("reportJson");
        if(text!=null) {
            try{result.put("report",mapper.readTree(text.toString()));}catch(IOException e){throw new ServiceException("评测记录读取失败",500);}
        }else result.put("report",null);
        return result;
    }
    public Map<String,Object> start(String requestId,String actor) {
        uuid(requestId);require(!stopping,"后台正在停止，请稍后重试");
        boolean[] created={false};
        String id=tx.execute(status -> {
            db.one("SELECT id FROM st_patrol_eval_guard WHERE id=1 FOR UPDATE");
            var same=db.rows("SELECT run_id,actor FROM st_patrol_eval_request WHERE request_id=? FOR UPDATE",requestId);
            if(!same.isEmpty()){require(actor.equals(s(same.get(0),"actor")),"提交标识已被使用");return s(same.get(0),"runId");}
            var active=db.rows("SELECT id FROM st_patrol_eval WHERE status IN ('queued','running') ORDER BY created_time LIMIT 1 FOR UPDATE");
            if(!active.isEmpty()) {
                String activeId=s(active.get(0),"id");
                db.update("INSERT INTO st_patrol_eval_request(request_id,run_id,actor) VALUES(?,?,?)",requestId,activeId,actor);
                return activeId;
            }
            JsonNode cfg;
            try{cfg=configuration();}catch(IOException e){throw new ServiceException("模型或训练环境尚未就绪，请先发布已完成训练的模型",409);}
            String runId=UUID.randomUUID().toString();
            int count=ThreadLocalRandom.current().nextInt(1,133);
            db.update("INSERT INTO st_patrol_eval(id,request_id,status,stage,model_name,model_sha256,dataset_sha256,created_by,image_count) VALUES(?,?,'queued','queued',?,?,?,?,?)",
                runId,requestId,cfg.path("modelName").asText(),cfg.path("modelSha256").asText(),cfg.path("datasetSha256").asText(),actor,count);
            db.update("INSERT INTO st_patrol_eval_request(request_id,run_id,actor) VALUES(?,?,?)",requestId,runId,actor);
            db.update("INSERT INTO st_audit(entity_id,action,reason,actor) VALUES(?,'patrol.evaluate',?,?)",runId,"HAIDA随机抽样巡逻演示，计划识别"+count+"张；非真实巡逻",actor);
            created[0]=true;return runId;
        });
        if(created[0]) {
            try{executor.submit(() -> evaluate(id));}catch(RejectedExecutionException e){fail(id,"后台正在停止，本次未执行，请重新启动仿真巡逻");}
        }
        var result=detail(id);result.put("reused",!created[0]);return result;
    }
    @EventListener(ApplicationReadyEvent.class)
    public void recover() {
        db.update("UPDATE st_patrol_eval SET status='failed',stage='failed',ended_time=NOW(3),error_message='服务重启中断了本次评测，请重新启动仿真巡逻；未生成完成报告' WHERE status IN ('queued','running')");
    }
    private void fail(String id,String message) {
        tx.executeWithoutResult(status -> {
            if(db.update("UPDATE st_patrol_eval SET status='failed',stage='failed',error_message=?,ended_time=NOW(3) WHERE id=? AND status IN ('queued','running')",message,id)>0)
                db.update("INSERT INTO st_audit(entity_id,action,reason,actor) VALUES(?,'patrol.failed',?,'system')",id,message);
        });
    }
    private void validateReport(JsonNode value,Map<String,Object> run) {
        require(value.path("runId").asText().equals(s(run,"id")) && value.path("modelSha256").asText().equals(s(run,"modelSha256"))
            && value.path("datasetSha256").asText().equals(s(run,"datasetSha256")),"评测来源校验失败");
        int count=((Number)run.get("imageCount")).intValue();
        require("haida-patrol-random-v2".equals(value.path("protocolVersion").asText()) && "test".equals(value.path("split").asText())
            && count>=1 && count<=132 && value.path("imageCount").asInt()==count && value.path("rows").size()==count,"评测数据不完整");
        require(value.path("poolImageCount").asInt()==132 && s(run,"id").equals(value.path("samplingSeed").asText())
            && "uniform-count-without-replacement".equals(value.path("samplingStrategy").asText()),"抽样来源无效");
        require(value.path("confidence").asDouble(-1)==.25 && value.path("matchIou").asDouble(-1)==.5
            && value.path("imgsz").asInt()==640 && value.path("nmsIou").asDouble(-1)==.7,"评测协议不一致");
        var ids=new HashSet<String>();int tp=0,fp=0,fn=0;
        for(var row:value.path("rows")) {
            require(row.path("id").asText().matches("data\\d+(?:_DJI)?_\\d+") && ids.add(row.path("id").asText()),"评测图片标识重复或无效");
            int t=row.path("tp").asInt(-1),f=row.path("fp").asInt(-1),n=row.path("fn").asInt(-1);
            require(t>=0 && f>=0 && n>=0 && t+f==row.path("predictionCount").asInt() && t+n==row.path("truthCount").asInt(),"评测计数不一致");
            require(row.path("predictions").isArray() && row.path("truths").isArray()
                && row.path("predictions").size()==t+f && row.path("truths").size()==t+n,"评测框数不一致");
            validateRatio(row,"precision",t,t+f);validateRatio(row,"recall",t,t+n);
            for(var prediction:row.path("predictions")) {
                double score=prediction.path("confidence").asDouble(-1);
                require(prediction.path("classId").asInt(-1)>=0 && prediction.path("classId").asInt(-1)<=1
                    && Double.isFinite(score) && score>=.25 && score<=1,"预测类别或置信度无效");
            }
            tp+=t;fp+=f;fn+=n;
        }
        require(tp==value.path("tp").asInt() && fp==value.path("fp").asInt() && fn==value.path("fn").asInt(),"评测统计校验失败");
        validateRatio(value,"precision",tp,tp+fp);validateRatio(value,"recall",tp,tp+fn);
        for(String key:List.of("map50","map5095")) {double number=value.path(key).asDouble(-1);require(Double.isFinite(number) && number>=0 && number<=1,"评测指标无效");}
    }
    private void validateRatio(JsonNode node,String key,int numerator,int denominator) {
        var value=node.path(key);
        if(denominator==0)require(value.isNull(),"无定义指标必须为空");
        else require(value.isNumber() && Double.isFinite(value.asDouble()) && Math.abs(value.asDouble()-(double)numerator/denominator)<1e-9,"指标计算不一致");
    }
    private void evaluate(String id) {
        Process process=null;
        try {
            if(db.update("UPDATE st_patrol_eval SET status='running',stage='verifying',started_time=NOW(3) WHERE id=? AND status='queued'",id)!=1)return;
            var run=db.one("SELECT "+META+" FROM st_patrol_eval WHERE id=?",id);
            var output=root.resolve("runs/patrol/"+id);
            Files.createDirectories(root.resolve("logs/patrol"));
            var builder=new ProcessBuilder(root.resolve(".venv/Scripts/python.exe").toString(),root.resolve("scripts/patrol_eval.py").toString(),
                "--run-id",id,"--model-sha",s(run,"modelSha256"),"--image-count",s(run,"imageCount"));
            builder.directory(root.toFile()).redirectErrorStream(true).redirectOutput(root.resolve("logs/patrol/"+id+".log").toFile());
            builder.environment().put("PYTHONUTF8","1");builder.environment().put("PYTHONUNBUFFERED","1");
            process=builder.start();child.set(process);
            long deadline=System.nanoTime()+Duration.ofMinutes(15).toNanos();String previous="";
            while(!process.waitFor(350,TimeUnit.MILLISECONDS)) {
                if(stopping || System.nanoTime()>deadline)throw new IOException("Evaluator timeout or shutdown");
                var progress=output.resolve("progress.json");
                if(Files.isRegularFile(progress))try {
                    String text=Files.readString(progress);
                    if(!text.equals(previous)) {
                        var node=mapper.readTree(text);String stage=node.path("stage").asText();int done=node.path("processed").asInt(-1);
                        if(Set.of("verifying","evaluating","rendering").contains(stage) && done>=0 && done<=((Number)run.get("imageCount")).intValue())
                            db.update("UPDATE st_patrol_eval SET stage=?,processed=? WHERE id=? AND status='running'",stage,done,id);
                        previous=text;
                    }
                }catch(IOException ignored){/* atomic rename may be briefly unavailable on Windows */}
            }
            if(process.exitValue()!=0)throw new IOException("Evaluator exited "+process.exitValue());
            var report=output.resolve("report.json");require(Files.isRegularFile(report) && Files.size(report)<8_000_000,"评测结果文件缺失或过大");
            byte[] bytes=Files.readAllBytes(report);var value=mapper.readTree(bytes);validateReport(value,run);
            for(var row:value.path("rows"))for(String kind:List.of("predicted","truth","original"))
                require(Files.isRegularFile(output.resolve(kind).resolve(row.path("id").asText()+".jpg")),"检测图片未完整保存");
            String text=new String(bytes,StandardCharsets.UTF_8),sha=hash(bytes);
            tx.executeWithoutResult(status -> {
                require(db.update("UPDATE st_patrol_eval SET status='completed',stage='completed',processed=image_count,ended_time=NOW(3),report_json=?,report_sha256=? WHERE id=? AND status='running'",text,sha,id)==1,"运行已中断，不能写入完成报告");
                db.update("INSERT INTO st_audit(entity_id,action,reason,actor) VALUES(?,'patrol.completed','HAIDA随机影像模型识别完成；非实机结果','system')",id);
            });
        }catch(Exception error) {
            LOG.warn("Patrol evaluation {} failed",id,error);
            fail(id,"评测未完成：请检查本机GPU、固定模型与数据完整性；诊断日志在ai/logs/patrol，修复后可重新运行");
        }finally {
            if(process!=null && process.isAlive()) {process.destroyForcibly();try{process.waitFor(5,TimeUnit.SECONDS);}catch(InterruptedException e){Thread.currentThread().interrupt();}}
            child.compareAndSet(process,null);
        }
    }
    public byte[] image(String id,String imageId,String kind) {
        uuid(id);require(Set.of("predicted","truth","original").contains(kind),"图片类型无效");
        require(imageId.matches("data\\d+(?:_DJI)?_\\d+"),"图片标识无效");
        var run=detail(id);require("completed".equals(s(run,"status")),"评测尚未完成，图片不可读取");
        var report=(JsonNode)run.get("report");boolean found=false;
        for(var row:report.path("rows"))if(imageId.equals(row.path("id").asText()))found=true;
        require(found,"图片不属于该次测试集");
        try {
            Path base=root.resolve("runs/patrol/"+id).toRealPath();
            String folder="predicted".equals(kind) && Files.isRegularFile(base.resolve("preview").resolve(imageId+".jpg")) ? "preview" : kind;
            Path file=base.resolve(folder).resolve(imageId+".jpg").toRealPath();
            require(file.startsWith(base) && Files.size(file)<10_000_000,"图片文件无效");
            byte[] data=Files.readAllBytes(file);require(data.length>2 && (data[0]&255)==255 && (data[1]&255)==216,"图片格式无效");return data;
        }catch(IOException e){throw new ServiceException("检测图片不可读取",404);}
    }
    @PreDestroy public void stop() {stopping=true;var process=child.get();if(process!=null)process.destroyForcibly();executor.shutdownNow();}
}
