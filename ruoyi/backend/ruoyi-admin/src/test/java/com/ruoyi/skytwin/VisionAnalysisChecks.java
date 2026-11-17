package com.ruoyi.skytwin;
import com.fasterxml.jackson.databind.*;
import com.fasterxml.jackson.databind.node.*;
import java.util.*;

/** Isolated server acceptance of calculator output and binding rules. No database or model. */
public class VisionAnalysisChecks {
    static int count=0;
    static void accept(Runnable action){action.run();count++;}
    static void reject(Runnable action){try{action.run();}catch(com.ruoyi.common.exception.ServiceException e){count++;return;}throw new AssertionError("Expected rejection");}
    public static void main(String[] args)throws Exception {
        var mapper=new ObjectMapper();String id=UUID.randomUUID().toString(),hash="a".repeat(64),model="b".repeat(64);
        var image=new EnvironmentImage(new byte[]{1},"image/png",hash,100,100,"fixture.png");
        ObjectNode result=mapper.createObjectNode();result.put("analysisId",id).put("imageSha256",hash).put("modelSha256",model).put("width",100).put("height",100).put("confidenceThreshold",.25);
        var predictions=result.putArray("predictions");var box=predictions.addObject();box.put("x",.1).put("y",.1).put("width",.5).put("height",.5).put("confidence",.8).put("label","garbage");
        accept(()->VisionAnalysisService.validateResult(result,id,image,model));
        for(String key:List.of("analysisId","imageSha256","modelSha256")) {var bad=result.deepCopy();bad.put(key,"forged");reject(()->VisionAnalysisService.validateResult(bad,id,image,model));}
        for(String key:List.of("width","height","confidenceThreshold")) {var bad=result.deepCopy();bad.put(key,9);reject(()->VisionAnalysisService.validateResult(bad,id,image,model));}
        for(String key:List.of("x","y","width","height","confidence")) {var bad=result.deepCopy();((ObjectNode)bad.path("predictions").get(0)).put(key,2);reject(()->VisionAnalysisService.validateResult(bad,id,image,model));}
        var bad=result.deepCopy();((ObjectNode)bad.path("predictions").get(0)).put("label","invented");reject(()->VisionAnalysisService.validateResult(bad,id,image,model));
        var empty=result.deepCopy();empty.putArray("predictions");accept(()->VisionAnalysisService.validateResult(empty,id,image,model));
        Map<String,Object> link=new HashMap<>(Map.of("status","completed","createdBy","fixture-operator","imageSha256",hash));
        accept(()->VisionAnalysisService.validateLink(link,image,"fixture-operator"));
        for(var pair:List.of(Map.entry("status","running"),Map.entry("createdBy","other-account"),Map.entry("imageSha256","changed"),Map.entry("discoveryId","already-linked"))){var changed=new HashMap<>(link);changed.put(pair.getKey(),pair.getValue());reject(()->VisionAnalysisService.validateLink(changed,image,"fixture-operator"));}
        System.out.println("PASS "+count+" vision server output/binding checks (isolated, no DB)");
    }
}
