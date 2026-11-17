package com.ruoyi.skytwin;
import java.nio.file.*;
import java.sql.*;
import java.time.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.function.Supplier;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.*;
import org.springframework.transaction.support.TransactionTemplate;
import static com.ruoyi.skytwin.OperationsRules.*;

/** Real service and MySQL acceptance, only a fresh disposable schema; never authenticates as a web user. */
public class OperationsWorkflowChecks {
    static int count;
    static void check(boolean ok,String message){if(!ok)throw new AssertionError(message);count++;}
    static void rejected(Runnable action){try{action.run();}catch(RuntimeException e){count++;return;}throw new AssertionError("Expected rejection");}
    static <T> T run(TransactionTemplate tx,Supplier<T> action){return tx.execute(status->action.get());}
    public static void main(String[] args)throws Exception {
        Path root=Path.of(args[0]).toAbsolutePath();Properties defaults=new Properties();try(var reader=Files.newBufferedReader(root.resolve("ruoyi/config/mysql-root.cnf"))){defaults.load(reader);}
        String password=defaults.getProperty("password","").replaceAll("^['\"]|['\"]$","");String url="jdbc:mysql://127.0.0.1:3307/",options="?useUnicode=true&characterEncoding=utf8&useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC";
        String schema="sky_ops_verify_"+UUID.randomUUID().toString().replace("-","");
        try(var admin=DriverManager.getConnection(url+options,"root",password)){
            admin.createStatement().execute("CREATE DATABASE "+schema+" CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci");
            try{
                var source=new DriverManagerDataSource(url+schema+options,"root",password);var jdbc=new JdbcTemplate(source);var db=new SkyRepository(jdbc);var tx=new TransactionTemplate(new DataSourceTransactionManager(source));
                var files=new ArrayList<Path>();try(var stream=Files.newDirectoryStream(root.resolve("ruoyi/backend/sql"),"sky_twin_v*.sql")){stream.forEach(files::add);}
                files.sort(Comparator.comparingInt(p->Integer.parseInt(p.getFileName().toString().replaceAll("sky_twin_v(\\d+).*","$1"))));
                for(var file:files)for(String statement:Files.readString(file).replaceAll("(?m)--.*$","").split(";"))if(statement.strip().toUpperCase().startsWith("CREATE TABLE"))jdbc.execute(statement);
                jdbc.update("INSERT INTO st_airspace_policy(id,revision) VALUES(1,0)");jdbc.update("INSERT INTO st_traffic_clock(id,tick) VALUES(1,0)");
                for(String id:List.of("S1","S2","V1","V2"))jdbc.update("INSERT INTO st_station(id,name,type,longitude,latitude) VALUES(?,?,?,?,?)",id,id,id.startsWith("V")?"vertiport":"takeoff",id.endsWith("1")?120.19:120.20,30.215);
                jdbc.update("INSERT INTO st_aircraft(id,name,type,model,longitude,latitude,battery,payload_capacity,seats) VALUES('A1','测试机','cargo','fixture',120.19,30.215,90,20,0),('E1','通勤机','evtol','fixture',120.19,30.215,100,20,4)");
                var mapper=new ObjectMapper().findAndRegisterModules();var flightRoutes=new FlightRoutes(db,mapper);var airspace=new AirspaceService(db,new AirspaceRecords(db,mapper),mapper,flightRoutes);var traffic=new TrafficService(db,flightRoutes,airspace,new TrafficRecords(db,mapper),mapper);
                var sky=new SkyService(db,airspace,new PositionService(db),flightRoutes,traffic);var routes=new RouteService(db,flightRoutes,airspace);var environment=new EnvironmentService(db,sky,routes,mapper);var logistics=new LogisticsService(db,sky);
                var tasks=new TaskOperationsService(db,sky,logistics,environment,routes,flightRoutes);var resources=new ResourceOperationsService(db,sky);var commute=new CommuteService(db,sky);var reports=new OperationsReportService(db,environment,mapper);
                var resourceInput=new OperationsInputs.Resource(UUID.randomUUID().toString(),"A1","charging","测试充电");var charging=run(tx,()->resources.start(resourceInput,"fixture"));String chargeId=s(charging,"id");
                check("charging".equals(s(db.one("SELECT status FROM st_aircraft WHERE id='A1'"),"status")),"charging blocks idle state");
                check(chargeId.equals(s(run(tx,()->resources.start(resourceInput,"fixture")),"id")),"resource request replay");
                Supplier<String> newTask=()->sky.createTask(new SkyInputs.Task("测试任务","environment","S1","S2",1.0,0,10.0,80.0,"fixture"),"fixture");
                String task=run(tx,newTask);rejected(()->run(tx,()->{sky.taskAction(task,"assign",new SkyInputs.Action("A1","test"),"fixture");return null;}));
                rejected(()->run(tx,()->resources.close(chargeId,new OperationsInputs.Close("降低电量",10.0),"fixture")));
                run(tx,()->resources.close(chargeId,new OperationsInputs.Close("完成仿真充电",100.0),"fixture"));check(n(db.one("SELECT battery FROM st_aircraft WHERE id='A1'"),"battery")==100,"charging persisted");
                rejected(()->run(tx,()->resources.close(chargeId,new OperationsInputs.Close("重复",100.0),"fixture")));
                run(tx,()->{sky.taskAction(task,"assign",new SkyInputs.Action("A1","fixture"),"fixture");return null;});
                jdbc.execute("CREATE TRIGGER ops_failure BEFORE INSERT ON st_resource_operation FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='isolated late failure'");
                var faultInput=new OperationsInputs.Resource(UUID.randomUUID().toString(),"A1","fault","故障测试");rejected(()->run(tx,()->resources.start(faultInput,"fixture")));
                check("assigned".equals(s(db.one("SELECT status FROM st_task WHERE id=?",task),"status")),"fault failure rolled back task termination");check(db.count("SELECT COUNT(*) FROM st_report WHERE task_id=?",task)==0,"fault failure rolled back task report");jdbc.execute("DROP TRIGGER ops_failure");
                var fault=run(tx,()->resources.start(faultInput,"fixture"));check("failed".equals(s(db.one("SELECT status FROM st_task WHERE id=?",task),"status")),"fault marks occupied task failed");
                run(tx,()->resources.close(s(fault,"id"),new OperationsInputs.Close("维修完成",100.0),"fixture"));
                var retryInput=new OperationsInputs.Retry(UUID.randomUUID().toString(),"重试测试",120);var retry=run(tx,()->tasks.retry(task,retryInput,"fixture"));String child=s(retry,"taskId");
                check(!child.equals(task)&&"created".equals(s(db.one("SELECT status FROM st_task WHERE id=?",child),"status")),"retry creates new task");
                check(child.equals(s(run(tx,()->tasks.retry(task,retryInput,"fixture")),"taskId")),"retry replay stable");
                rejected(()->run(tx,()->tasks.retry(task,new OperationsInputs.Retry(UUID.randomUUID().toString(),"duplicate",120),"fixture")));
                check("failed".equals(s(db.one("SELECT status FROM st_task WHERE id=?",task),"status")),"original task remains failed");
                check(((Number)tasks.tasks(1,1,"","","").get("total")).intValue()==2&&((List<?>)tasks.tasks(1,1,"","","").get("rows")).size()==1,"server pagination full total");
                jdbc.update("UPDATE st_task SET created_time=DATE_SUB(NOW(),INTERVAL 31 MINUTE) WHERE id=?",child);var paged=tasks.tasks(1,20,"created","",child);check(!s((Map<String,Object>)((List<?>)paged.get("rows")).get(0),"reminder").isBlank(),"pending reminder");
                run(tx,()->{resources.capacity("S1",new OperationsInputs.Capacity(1,"test"),"fixture");return null;});jdbc.update("UPDATE st_task SET status='executing' WHERE id=?",child);rejected(()->OperationsRules.assertStationLaunch(db,db.one("SELECT * FROM st_task WHERE id=?",task)));jdbc.update("UPDATE st_task SET status='cancelled' WHERE id=?",child);
                String orderId=run(tx,()->logistics.create(new LogisticsInputs.Create("测试包裹",1.0,"S1","S2",120,"fixture"),"fixture"));String logisticTask=s(db.one("SELECT task_id FROM st_logistics_order WHERE id=?",orderId),"taskId");run(tx,()->{sky.taskAction(logisticTask,"cancel",new SkyInputs.Action(null,"fixture"),"fixture");return null;});
                var newOrder=run(tx,()->tasks.retry(logisticTask,new OperationsInputs.Retry(UUID.randomUUID().toString(),"重试配送",120),"fixture"));check(db.count("SELECT COUNT(*) FROM st_logistics_order WHERE task_id=?",newOrder.get("taskId"))==1,"logistics retry preserves order workflow");
                var departure=LocalDateTime.now().plusHours(1);var flightInput=new OperationsInputs.Flight(UUID.randomUUID().toString(),"并发座位测试","V1","V2",departure,4,"fixture");var flight=run(tx,()->commute.create(flightInput,"fixture"));String fid=s(flight,"id");
                check(fid.equals(s(run(tx,()->commute.create(flightInput,"fixture")),"id")),"flight create replay");
                var executor=Executors.newFixedThreadPool(8);try{
                    var futures=new ArrayList<Future<Boolean>>();for(int i=0;i<8;i++)futures.add(executor.submit(()->{try{run(tx,()->commute.book(fid,new OperationsInputs.Booking(UUID.randomUUID().toString(),1),"fixture"));return true;}catch(com.ruoyi.common.exception.ServiceException e){return false;}}));
                    int successes=0;for(var future:futures)if(future.get(20,TimeUnit.SECONDS))successes++;check(successes==4,"exactly four concurrent seats accepted");check(n(commute.detail(fid),"bookedSeats")==4,"no overselling");
                }finally{executor.shutdownNow();}
                String booking=s(((List<Map<String,Object>>)commute.detail(fid).get("bookings")).get(0),"id");rejected(()->run(tx,()->{commute.cancelBooking(booking,"other");return null;}));
                run(tx,()->{commute.cancelBooking(booking,"fixture");return null;});check(n(commute.detail(fid),"bookedSeats")==3,"cancel releases seat");
                var activated=run(tx,()->commute.action(fid,"activate",new OperationsInputs.FlightAction(1,null,"锁定名单"),"fixture"));String commuteTask=s(activated,"taskId");check(n(db.one("SELECT passengers FROM st_task WHERE id=?",commuteTask),"passengers")==3,"task passenger count is confirmed bookings");
                rejected(()->run(tx,()->commute.book(fid,new OperationsInputs.Booking(UUID.randomUUID().toString(),1),"fixture")));
                rejected(()->OperationsRules.assertStationLaunch(db,db.one("SELECT * FROM st_task WHERE id=?",commuteTask)));
                var delayed=run(tx,()->commute.action(fid,"delay",new OperationsInputs.FlightAction(2,LocalDateTime.now().plusMinutes(1),"调整班次"),"fixture"));check((int)n(delayed,"revision")==3,"delay optimistic version");
                rejected(()->run(tx,()->commute.action(fid,"cancel",new OperationsInputs.FlightAction(2,null,"旧版本"),"fixture")));
                run(tx,()->commute.action(fid,"cancel",new OperationsInputs.FlightAction(3,null,"取消班次"),"fixture"));check("cancelled".equals(s(db.one("SELECT status FROM st_task WHERE id=?",commuteTask),"status")),"cancel flight cancels unstarted task");
                var reportInput=new OperationsInputs.Report(UUID.randomUUID().toString(),"task",task);var report=run(tx,()->reports.create(reportInput,"fixture"));String rid=s(report,"id");
                check(rid.equals(s(run(tx,()->reports.create(reportInput,"fixture")),"id")),"report create replay");
                run(tx,()->reports.edit(rid,new OperationsInputs.ReportEdit(1,"人工修改内容","manual",false),"fixture"));check(!s(reports.version(rid,1),"content").equals("人工修改内容"),"old report version immutable");
                rejected(()->run(tx,()->reports.edit(rid,new OperationsInputs.ReportEdit(1,"旧版本","manual",false),"fixture")));
                run(tx,()->reports.edit(rid,new OperationsInputs.ReportEdit(2,"人工已核对仿真证据","manual",true),"fixture"));rejected(()->run(tx,()->reports.edit(rid,new OperationsInputs.ReportEdit(3,"不可改","manual",false),"fixture")));
                var draft=run(tx,()->reports.create(new OperationsInputs.Report(UUID.randomUUID().toString(),"task",child),"fixture"));jdbc.update("UPDATE st_task SET reason='证据变化' WHERE id=?",child);rejected(()->run(tx,()->reports.edit(s(draft,"id"),new OperationsInputs.ReportEdit(1,"旧证据","manual",true),"fixture")));
                // Candidate path bypasses a rectangle and still passes the existing policy engine.
                var start=new RouteEngine.Waypoint(120.19,30.215);var end=new RouteEngine.Waypoint(120.20,30.215);var rect=new DetourPlanner.Rect(120.194,30.214,120.196,30.216);
                var via=DetourPlanner.plan(List.of(start,end),List.of(rect));check(!via.isEmpty(),"blocked straight path gets detour");var path=new ArrayList<RouteEngine.Waypoint>();path.add(start);path.addAll(via);path.add(end);for(int i=1;i<path.size();i++)check(!DetourPlanner.crosses(path.get(i-1),path.get(i),rect),"each detour segment avoids rectangle");
                String planned=run(tx,newTask);
                jdbc.update("INSERT INTO st_airspace_zone(id,name,type,west,south,east,north,min_altitude,max_altitude,enabled,created_by,updated_by,reason) VALUES('AZ-test','测试禁飞区','no_fly',120.194,30.214,120.196,30.216,0,120,1,'fixture','fixture','test')");
                var suggestion=run(tx,()->routes.suggest(planned,new RouteInputs.Save(1,List.of(),"自动建议测试"),"fixture"));
                check(Boolean.TRUE.equals(suggestion.get("allowed")),"candidate passes existing full airspace validation");check(db.count("SELECT COUNT(*) FROM st_task_route WHERE task_id=?",planned)==1,"suggestion never saves route automatically");
                run(tx,()->routes.save(planned,new RouteInputs.Save(1,(List<RouteInputs.Waypoint>)suggestion.get("suggestedWaypoints"),"审查后保存"),"fixture"));check(flightRoutes.current(planned,false).revision()==2,"candidate saved by original versioned route service");
                var capacityTime=LocalDateTime.now().plusHours(5);
                var cf1=run(tx,()->commute.create(new OperationsInputs.Flight(UUID.randomUUID().toString(),"未来容量1","V1","V2",capacityTime,4,"fixture"),"fixture"));
                var cf2=run(tx,()->commute.create(new OperationsInputs.Flight(UUID.randomUUID().toString(),"未来容量2","V1","V2",capacityTime,4,"fixture"),"fixture"));
                rejected(()->run(tx,()->{resources.capacity("V1",new OperationsInputs.Capacity(1,"不能破坏预约"),"fixture");return null;}));
                run(tx,()->commute.action(s(cf1,"id"),"cancel",new OperationsInputs.FlightAction(1,null,"清理测试班次"),"fixture"));
                run(tx,()->commute.action(s(cf2,"id"),"cancel",new OperationsInputs.FlightAction(1,null,"清理测试班次"),"fixture"));
                run(tx,()->{resources.capacity("V1",new OperationsInputs.Capacity(1,"测试预约容量"),"fixture");return null;});
                var futureDeparture=LocalDateTime.now().plusHours(3);run(tx,()->commute.create(new OperationsInputs.Flight(UUID.randomUUID().toString(),"容量测试1","V1","V2",futureDeparture,4,"fixture"),"fixture"));
                rejected(()->run(tx,()->commute.create(new OperationsInputs.Flight(UUID.randomUUID().toString(),"容量测试2","V1","V2",futureDeparture,4,"fixture"),"fixture")));
                try{DetourPlanner.plan(List.of(new RouteEngine.Waypoint(120.195,30.215),end),List.of(rect));throw new AssertionError("inside exclusion should fail");}catch(IllegalArgumentException e){count++;}
                var ops=new OperationsController(db,tasks,resources,commute,reports,null);
                var spatial=(Map<String,Object>)ops.spatial(120.185,120.191,30.21,30.22).get("data");
                check(((Number)spatial.get("total")).longValue()>0,"spatial query includes task endpoint inside selected box");
                check(((List<?>)spatial.get("rows")).size()<=100,"spatial query bounded result page");
                var outside=(Map<String,Object>)ops.spatial(121,122,31,32).get("data");check(((Number)outside.get("total")).longValue()==0,"outside box returns no fabricated tasks");
                rejected(()->ops.spatial(Double.NaN,121,30,31));rejected(()->ops.spatial(121,120,30,31));rejected(()->ops.spatial(120,181,30,31));
                var vision=new VisionAnalysisService(db,mapper,new DataSourceTransactionManager(source),root.resolve("ai").toString());
                String analysisId=UUID.randomUUID().toString();byte[] imageBytes=new byte[]{1,2,3};
                jdbc.update("INSERT INTO st_env_analysis(id,request_id,status,created_by,image_bytes,image_mime,image_sha256,image_width,image_height,model_sha256,model_name) VALUES(?,?,'completed','fixture',?,'image/png',?,1,1,?,'fixture')",analysisId,UUID.randomUUID().toString(),imageBytes,"a".repeat(64),"b".repeat(64));
                check(Arrays.equals(imageBytes,(byte[])vision.image(analysisId).get("imageBytes")),"image view returns the same original analysis bytes");
                var response=new EnvironmentController(environment,vision).analysisImage(analysisId);
                check(response.getHeaders().getCacheControl().contains("no-store")&&"nosniff".equals(response.getHeaders().getFirst("X-Content-Type-Options")),"analysis image response disables caching and sniffing");
                System.out.println("PASS "+count+" isolated operations service/MySQL checks (8 concurrent bookings, no production writes)");
            }finally{admin.createStatement().execute("DROP DATABASE "+schema);}
        }
    }
}
