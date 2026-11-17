package com.ruoyi.skytwin;
import java.time.*;
public class PositionRulesChecks {
    private static int checks;
    private static void check(boolean ok) { checks++;if(!ok) throw new AssertionError("Position check "+checks); }
    public static void main(String[] args) {
        Instant now=Instant.parse("2026-10-19T00:00:00Z");
        var current=new PositionRules.Point(now,120.19,30.215,240);
        var previous=new PositionRules.Point(now.minusSeconds(1),120.19,30.215,240);
        check(PositionRules.verdict(current,now,1,0,true,previous).equals("accepted"));
        check(PositionRules.verdict(current,now,0,0,true,previous).equals("out_of_order_sequence"));
        check(PositionRules.verdict(current,now,1,0,false,previous).equals("no_fix"));
        check(PositionRules.verdict(current,now.plusSeconds(31),1,0,true,null).equals("stale_timestamp"));
        check(PositionRules.verdict(current,now.plusSeconds(30),1,0,true,null).equals("accepted"));
        check(PositionRules.verdict(current,now.minusSeconds(5),1,0,true,null).equals("accepted"));
        check(PositionRules.verdict(current,now.minusMillis(5001),1,0,true,null).equals("future_timestamp"));
        check(PositionRules.verdict(current,now,1,0,true,current).equals("out_of_order_timestamp"));
        check(PositionRules.time("2026-10-19T08:00:00+08:00").equals(now));
        for(String invalid:new String[]{"2026-10-19T08:00:00","garbage","2026-10-19T00:00:00.000001Z","+10000-01-01T00:00:00Z","0999-01-01T00:00:00Z"}) {
            boolean rejected=false;try { PositionRules.time(invalid); } catch(RuntimeException e) { rejected=true; } check(rejected);
        }
        check(PositionRules.verdict(new PositionRules.Point(now,Double.NaN,30,0),now,1,0,true,null).equals("invalid_coordinates"));
        check(PositionRules.verdict(new PositionRules.Point(now,181,30,0),now,1,0,true,null).equals("invalid_coordinates"));
        check(PositionRules.verdict(new PositionRules.Point(now,121.19,30.215,240),now,1,0,true,previous).equals("position_jump"));
        check(PositionRules.verdict(new PositionRules.Point(now,120.19,30.215,281),now,1,0,true,previous).equals("position_jump"));
        check(PositionRules.verdict(new PositionRules.Point(now,120.19,30.215,280),now,1,0,true,previous).equals("accepted"));
        for(int i=0;i<100;i++) {
            var p=new PositionRules.Point(now,120.19+i*.000001,30.215,240);
            check(PositionRules.verdict(p,now,1,0,true,previous).equals("accepted"));
        }
        System.out.println("PASS: "+checks+" positioning rule checks");
    }
}
