package com.ruoyi.skytwin;
import java.util.*;
import com.ruoyi.common.exception.ServiceException;

public final class OperationsRules {
    private OperationsRules(){}
    static String s(Map<String,Object> row,String key){return Objects.toString(row.get(key),"");}
    static double n(Map<String,Object> row,String key){return ((Number)row.get(key)).doubleValue();}
    static void require(boolean ok,String message){if(!ok)throw new ServiceException(message,409);}
    static String id(String prefix){return prefix+UUID.randomUUID().toString().replace("-","");}
    static void uuid(String id){try{require(UUID.fromString(id).toString().equals(id),"请求编号无效");}catch(IllegalArgumentException e){throw new ServiceException("请求编号无效",400);}}
    static void audit(SkyRepository db,String id,String action,String reason,String actor){db.update("INSERT INTO st_audit(entity_id,action,reason,actor) VALUES(?,?,?,?)",id,action,reason,actor);}
    static Map<String,Object> page(SkyRepository db,String select,String from,String where,List<Object> args,int page,int size,String order){
        require(page>=1&&page<=100000&&size>=1&&size<=100,"页码或页大小无效（每页1～100）");
        long total=db.count("SELECT COUNT(*) "+from+where,args.toArray());
        var parameters=new ArrayList<>(args);parameters.add(size);parameters.add((page-1)*size);
        return Map.of("rows",db.rows(select+from+where+order+" LIMIT ? OFFSET ?",parameters.toArray()),"total",total,"page",page,"size",size);
    }
    static int stationCapacity(SkyRepository db,String station){
        var rows=db.rows("SELECT capacity FROM st_station_capacity WHERE station_id=?",station);
        return rows.isEmpty()?200:((Number)rows.get(0).get("capacity")).intValue();
    }
    public static void assertStationLaunch(SkyRepository db,Map<String,Object> task){
        for(String key:List.of("startStationId","endStationId")){
            String station=s(task,key);
            long used=db.count("SELECT COUNT(*) FROM st_task WHERE status='executing' AND (start_station_id=? OR end_station_id=?)",station,station);
            require(used<stationCapacity(db,station),"起降场全航程保守占用已达到配置容量，请错峰执行");
        }
        var flights=db.rows("SELECT departure_at FROM st_commute_flight WHERE task_id=? AND status='scheduled'",task.get("id"));
        if(!flights.isEmpty()){
            var departure=java.time.LocalDateTime.parse(s(flights.get(0),"departureAt"));
            var now=java.time.LocalDateTime.now();
            require(!now.isBefore(departure.minusMinutes(5))&&!now.isAfter(departure.plusMinutes(15)),"不在班次仿真起飞窗口内，请先调整班次时间");
        }
    }
}
