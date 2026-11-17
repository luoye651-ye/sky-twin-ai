package com.ruoyi.skytwin;
import java.util.UUID;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
/** Deliberately no FK to locked task rows: denials survive the caller's rollback. */
@Service
public class TrafficRecords {
    private final SkyRepository db;private final ObjectMapper mapper;
    public TrafficRecords(SkyRepository db,ObjectMapper mapper) { this.db=db;this.mapper=mapper; }
    @Transactional(propagation=Propagation.REQUIRES_NEW)
    public void save(String taskId,boolean allowed,Object evidence,String actor) {
        try { db.update("INSERT INTO st_traffic_check(id,task_id,allowed,details_json,created_by) VALUES(?,?,?,?,?)",
            "TC-"+UUID.randomUUID().toString().replace("-",""),taskId,allowed,mapper.writeValueAsString(evidence),actor); }
        catch(com.fasterxml.jackson.core.JsonProcessingException e) { throw new IllegalStateException("冲突证据保存失败",e); }
    }
}
