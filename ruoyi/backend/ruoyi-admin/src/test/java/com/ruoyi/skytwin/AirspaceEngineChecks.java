package com.ruoyi.skytwin;

import java.time.LocalDateTime;
import java.util.*;
import static com.ruoyi.skytwin.AirspaceEngine.*;

public final class AirspaceEngineChecks {
    private static final LocalDateTime NOW=LocalDateTime.of(2026,10,19,10,0);
    private static final Flight FLIGHT=new Flight("t","test",120.19,30.215,120.193,30.215,60,20);
    private static int checks=0;
    private static void check(boolean value,String name) { if(!value) throw new AssertionError(name);checks++; }
    private static Zone zone(String type,double min,double max,LocalDateTime start,LocalDateTime end) {
        return new Zone("z","zone",type,120.191,30.214,120.192,30.216,min,max,start,end,true);
    }
    private static Check run(Zone zone) { return AirspaceEngine.check(FLIGHT,List.of(zone),NOW,3,NOW); }
    public static void main(String[] args) {
        var blocked=run(zone("no_fly",0,120,null,null));
        check(!blocked.allowed() && blocked.violations().size()==1,"crossing blocked");
        check(blocked.violations().get(0).phase().equals("cruise"),"phase identified");
        check(blocked.violations().get(0).rule().west()==120.191 && blocked.violations().get(0).rule().maxAltitude()==120,"historical rule geometry and altitude retained");
        check(Math.abs(blocked.violations().get(0).from().offsetSeconds()-7.3333333)<.00001,"continuous entry time");
        check(run(zone("no_fly",61,120,null,null)).allowed(),"different height allowed; visual lift irrelevant");
        check(run(zone("height_limit",0,60,null,null)).allowed(),"ceiling equality allowed");
        check(!run(zone("height_limit",0,59.9,null,null)).allowed(),"ceiling exceed rejected");
        check(run(zone("no_fly",0,120,NOW.plusSeconds(15),null)).allowed(),"zone starts after exit");
        check(run(zone("no_fly",0,120,null,NOW.plusSeconds(7))).allowed(),"zone ends before entry");
        check(!run(zone("no_fly",0,120,NOW.plusSeconds(9),NOW.plusSeconds(10))).allowed(),"overlapping time window");
        var startZone=new Zone("z","start","no_fly",120.189,30.214,120.1901,30.216,20,40,null,null,true);
        check(!run(startZone).allowed() && run(startZone).violations().get(0).phase().equals("takeoff"),"vertical takeoff crosses altitude band");
        var endZone=new Zone("z","end","height_limit",120.1929,30.214,120.194,30.216,0,30,NOW.plusSeconds(18),null,true);
        check(!run(endZone).allowed() && run(endZone).violations().get(0).phase().equals("landing"),"landing height checked");
        var thin=new Zone("z","thin","no_fly",120.191234,30.214,120.1912341,30.216,0,100,null,null,true);
        check(!run(thin).allowed(),"sub-second thin region cannot fall between samples");
        var tangent=new Zone("z","edge","no_fly",120.191,30.215,120.192,30.216,0,100,null,null,true);
        check(!run(tangent).allowed(),"spatial boundary included");
        var disabled=new Zone("z","disabled","no_fly",120.191,30.214,120.192,30.216,0,100,null,null,false);
        check(run(disabled).allowed(),"disabled ignored");
        check(run(zone("no_fly",0,120,LocalDateTime.of(5000,1,1,0,0),null)).allowed(),"distant date cannot overflow duration");
        var startsAtBoundary=new Zone("z","boundary","no_fly",120.1915,30.214,120.192,30.216,0,100,null,NOW.plusSeconds(10),true);
        check(run(startsAtBoundary).allowed(),"end instant excluded");
        var startInclusive=new Zone("z","boundary","no_fly",120.1915,30.214,120.192,30.216,0,100,NOW.plusSeconds(10),NOW.plusSeconds(11),true);
        check(!run(startInclusive).allowed(),"start instant included");
        check(AirspaceEngine.check(FLIGHT,List.of(),NOW,1,NOW).route().get(3).offsetSeconds()==20,"flight duration matches simulator");
        var random=new Random(88);
        for(int i=0;i<100;i++) {
            double lon=120.1901+random.nextDouble()*.0028;
            var narrow=new Zone("z","narrow","no_fly",lon,30.214,lon+.0000001,30.216,59,61,null,null,true);
            check(!run(narrow).allowed(),"random narrow crossing "+i);
        }
        System.out.println("PASS "+checks+" airspace continuous geometry/time/height checks");
    }
}
