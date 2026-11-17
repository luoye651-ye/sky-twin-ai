package com.ruoyi.skytwin;
import com.fasterxml.jackson.databind.*;
import java.nio.file.*;
import java.sql.*;
import java.time.Instant;
import java.util.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.jdbc.datasource.init.ScriptUtils;
import org.springframework.core.io.FileSystemResource;
import org.springframework.transaction.support.TransactionTemplate;

/** Real Java services and MySQL transactions in a disposable, uniquely named schema. No login bypass. */
public class VisionWorkflowChecks {
    static int count;
    static void check(boolean ok,String message){if(!ok)throw new AssertionError(message);count++;}
    static void rejected(Runnable action){try{action.run();}catch(RuntimeException e){count++;return;}throw new AssertionError("Expected transaction failure");}
    public static void main(String[] args)throws Exception {
        Path root=Path.of(args[0]).toAbsolutePath();String analysisId=args[1];
        if(!analysisId.matches("[a-f0-9-]{36}"))throw new IllegalArgumentException();
        Properties defaults=new Properties();try(var reader=Files.newBufferedReader(root.resolve("ruoyi/config/mysql-root.cnf"))){defaults.load(reader);}
        String password=defaults.getProperty("password","").replaceAll("^['\"]|['\"]$", "");
        String url="jdbc:mysql://127.0.0.1:3307/";
        String options="?useUnicode=true&characterEncoding=utf8&useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC";
        String schema="sky_verify_"+UUID.randomUUID().toString().replace("-","");
        try(var admin=DriverManager.getConnection(url+options,"root",password)){
            admin.createStatement().execute("CREATE DATABASE "+schema+" CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci");
            try{
                var dataSource=new DriverManagerDataSource(url+schema+options,"root",password);
                var jdbc=new JdbcTemplate(dataSource);var db=new SkyRepository(jdbc);var tx=new TransactionTemplate(new DataSourceTransactionManager(dataSource));
                jdbc.execute("CREATE TABLE st_task(id VARCHAR(40) PRIMARY KEY,title VARCHAR(80),type VARCHAR(24),status VARCHAR(24),aircraft_id VARCHAR(40),progress DOUBLE DEFAULT 0,duration_seconds INT DEFAULT 20) ENGINE=InnoDB");
                jdbc.execute("CREATE TABLE st_event(id BIGINT AUTO_INCREMENT PRIMARY KEY,task_id VARCHAR(40),aircraft_id VARCHAR(40),severity VARCHAR(10),title VARCHAR(200),status VARCHAR(20) DEFAULT 'open') ENGINE=InnoDB");
                jdbc.execute("CREATE TABLE st_traffic_clock(id INT PRIMARY KEY,tick BIGINT)");jdbc.update("INSERT INTO st_traffic_clock VALUES(1,0)");
                jdbc.execute("CREATE TABLE st_audit(id BIGINT AUTO_INCREMENT PRIMARY KEY,entity_id VARCHAR(40),action VARCHAR(80),reason VARCHAR(500),actor VARCHAR(64),created_time DATETIME DEFAULT CURRENT_TIMESTAMP)");
                try(var connection=dataSource.getConnection()){
                    ScriptUtils.executeSqlScript(connection,new FileSystemResource(root.resolve("ruoyi/backend/sql/sky_twin_v8_environment.sql")));
                    ScriptUtils.executeSqlScript(connection,new FileSystemResource(root.resolve("ruoyi/backend/sql/sky_twin_v10_vision.sql")));
                    ScriptUtils.executeSqlScript(connection,new FileSystemResource(root.resolve("ruoyi/backend/sql/sky_twin_v10_vision.sql")));
                }
                count++;
                jdbc.update("INSERT INTO st_task(id,title,type,status,aircraft_id) VALUES('fixture-patrol','测试巡检','environment','completed','fixture-aircraft')");
                var mapper=new ObjectMapper().findAndRegisterModules();var service=new EnvironmentService(db,null,null,mapper);
                Path folder=root.resolve("ai/runs/vision/"+analysisId);var image=EnvironmentImage.read(Files.readAllBytes(folder.resolve("input.image")),"fixture.jpg");
                String raw=Files.readString(folder.resolve("result.json"));var result=mapper.readTree(raw);
                VisionAnalysisService.validateResult(result,analysisId,image,result.path("modelSha256").asText());count++;
                jdbc.update("INSERT INTO st_env_analysis(id,request_id,status,created_by,image_bytes,image_mime,image_sha256,image_width,image_height,model_sha256,model_name,result_json) VALUES(?,?,'completed','fixture-operator',?,?,?,?,?,?,'released-fixture',?)",
                    analysisId,UUID.randomUUID().toString(),image.bytes(),image.mime(),image.sha256(),image.width(),image.height(),result.path("modelSha256").asText(),raw);
                var annotations=List.of(new EnvironmentInputs.Box(.1,.1,.2,.2,"人工选择框"));
                var input=new EnvironmentInputs.Discovery(UUID.randomUUID().toString(),"fixture-patrol","测试发现",120.19,30.215,Instant.now(),"simulation",annotations,analysisId);
                var discovery=tx.execute(status->service.create(input,image,"fixture-operator"));String id=discovery.get("id").toString();
                check("pending_review".equals(discovery.get("status")),"must await human review");
                check(db.count("SELECT COUNT(*) FROM st_event")==0,"inference never creates event directly");
                check("model_assisted_manual_review".equals(discovery.get("analysisSource")),"provenance must remain explicit");
                check(id.equals(tx.execute(status->service.create(input,image,"fixture-operator")).get("id")),"same request replay returns original");
                var duplicate=new EnvironmentInputs.Discovery(UUID.randomUUID().toString(),"fixture-patrol","重复",120.19,30.215,Instant.now(),"simulation",annotations,analysisId);
                rejected(()->tx.execute(status->service.create(duplicate,image,"other-account")));
                rejected(()->tx.execute(status->service.create(duplicate,image,"fixture-operator")));
                check(db.count("SELECT COUNT(*) FROM st_env_discovery")==1,"no duplicate discovery");
                var review=new EnvironmentInputs.Review("confirm","medium","人工复核确认，仅测试");
                var confirmed=tx.execute(status->service.review(id,review,"fixture-operator"));
                check("confirmed".equals(confirmed.get("status")) && db.count("SELECT COUNT(*) FROM st_event")==1,"review creates exactly one event");
                check(confirmed.get("visionAnalysis")!=null,"original predictions remain linked");
                rejected(()->tx.execute(status->service.review(id,review,"fixture-operator")));
                check(db.count("SELECT COUNT(*) FROM st_event")==1,"duplicate review creates no event");
                // A failure after event INSERT must roll the event back in the same transaction.
                var manual=new EnvironmentInputs.Discovery(UUID.randomUUID().toString(),"fixture-patrol","回滚测试",120.19,30.215,Instant.now(),"simulation",annotations,null);
                String manualId=tx.execute(status->service.create(manual,image,"fixture-operator")).get("id").toString();
                jdbc.execute("CREATE TRIGGER fixture_review_failure BEFORE UPDATE ON st_env_discovery FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='isolated injected failure'");
                rejected(()->tx.execute(status->service.review(manualId,review,"fixture-operator")));
                check(db.count("SELECT COUNT(*) FROM st_event")==1,"late failure rolls back event INSERT");
                check("pending_review".equals(service.detail(manualId).get("status")),"failed review preserves original state");
                System.out.println("PASS "+count+" isolated Java/MySQL vision workflow checks; no production schema writes");
            }finally{admin.createStatement().execute("DROP DATABASE "+schema);}
        }
    }
}
