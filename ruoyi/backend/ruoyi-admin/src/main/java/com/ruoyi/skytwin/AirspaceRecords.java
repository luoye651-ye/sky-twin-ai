package com.ruoyi.skytwin;

import java.util.UUID;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AirspaceRecords {
    private final SkyRepository db;private final ObjectMapper mapper;
    public AirspaceRecords(SkyRepository db,ObjectMapper mapper) { this.db=db;this.mapper=mapper; }
    @Transactional(propagation=Propagation.REQUIRES_NEW)
    public void save(AirspaceEngine.Check result,String entry,String actor) {
        String id="AC-"+UUID.randomUUID().toString().replace("-","");
        try {
            db.update("INSERT INTO st_airspace_check(id,task_id,task_title,entry,allowed,rule_revision,departure_at,details_json,created_by) VALUES(?,?,?,?,?,?,?,?,?)",
                id,result.taskId(),result.taskTitle(),entry,result.allowed(),result.ruleRevision(),result.departureAt(),mapper.writeValueAsString(result),actor);
            db.update("INSERT INTO st_audit(entity_id,action,reason,actor) VALUES(?,?,?,?)",id,
                result.allowed()?"airspace.pass":"airspace.block",entry+"："+(result.allowed()?"空域校验通过":"空域校验拒绝"),actor);
        } catch(JsonProcessingException ex) { throw new IllegalStateException("空域检查记录保存失败",ex); }
    }
}
