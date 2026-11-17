package com.ruoyi.skytwin;
import java.util.*;
import java.time.LocalDateTime;
public class RouteEngineChecks {
    private static int checks;
    private static void check(boolean ok) { checks++;if(!ok) throw new AssertionError("Route check "+checks); }
    private static void rejected(Runnable work) { boolean rejected=false;try { work.run(); } catch(IllegalArgumentException e) { rejected=true; }check(rejected); }
    public static void main(String[] args) {
        var from=new RouteEngine.Waypoint(120.19,30.215);var to=new RouteEngine.Waypoint(120.193,30.215);
        var direct=RouteEngine.build(1,from,to,List.of(),10,60,null);
        check(direct.points().size()==4 && direct.durationSeconds()==20);
        var via=List.of(new RouteEngine.Waypoint(120.19,30.225),new RouteEngine.Waypoint(120.193,30.225));
        var route=RouteEngine.build(2,from,to,via,10,60,null);
        check(route.points().size()==6 && route.distanceMeters()>direct.distanceMeters()*5 && route.durationSeconds()>20);
        check(route.durationSeconds()==(int)Math.ceil(route.distanceMeters()/80));
        check(RouteEngine.at(route.points(),-1).altitude()==0 && RouteEngine.at(route.points(),999).altitude()==0);
        check(RouteEngine.at(route.points(),route.durationSeconds()*.05).altitude()==30);
        check(Math.abs(RouteEngine.at(route.points(),route.durationSeconds()*.95).altitude()-30)<1e-7);
        for(int i=1;i<route.points().size();i++) check(route.points().get(i).offsetSeconds()>route.points().get(i-1).offsetSeconds());
        for(var corner:route.points()) {
            var p=RouteEngine.at(route.points(),corner.offsetSeconds());
            check(Math.abs(p.longitude()-corner.longitude())<1e-9 && Math.abs(p.latitude()-corner.latitude())<1e-9 && Math.abs(p.altitude()-corner.altitude())<1e-9);
        }
        var now=LocalDateTime.of(2026,10,19,10,0);
        var zone=new AirspaceEngine.Zone("z","middle","no_fly",120.191,30.2147,120.192,30.2153,0,120,null,null,true);
        check(!AirspaceEngine.checkPath("t","direct",direct.points(),List.of(zone),now,1,now).allowed());
        check(AirspaceEngine.checkPath("t","detour",route.points(),List.of(zone),now,1,now).allowed());
        // A narrow rectangle on a later leg must be detected even between discrete simulator ticks.
        var later=new AirspaceEngine.Zone("later","later-leg","no_fly",120.1929,30.2199,120.1931,30.2201,0,120,null,null,true);
        check(!AirspaceEngine.checkPath("t","detour",route.points(),List.of(later),now,1,now).allowed());
        var ceiling=new AirspaceEngine.Zone("limit","limit","height_limit",120.189,30.224,120.194,30.226,0,60,null,null,true);
        check(AirspaceEngine.checkPath("t","detour",route.points(),List.of(ceiling),now,1,now).allowed());
        var low=new AirspaceEngine.Zone("low","low","height_limit",120.189,30.224,120.194,30.226,0,59,null,null,true);
        check(!AirspaceEngine.checkPath("t","detour",route.points(),List.of(low),now,1,now).allowed());
        var future=new AirspaceEngine.Zone("future","future","no_fly",120.189,30.224,120.194,30.226,0,120,now.plusSeconds(1000),null,true);
        check(AirspaceEngine.checkPath("t","detour",route.points(),List.of(future),now,1,now).allowed());
        rejected(()->RouteEngine.build(1,from,to,List.of(from),10,60,null));
        rejected(()->RouteEngine.build(1,from,to,Collections.nCopies(25,from),10,60,null));
        rejected(()->RouteEngine.build(1,from,to,List.of(new RouteEngine.Waypoint(Double.NaN,30)),10,60,null));
        rejected(()->RouteEngine.build(1,from,to,List.of(new RouteEngine.Waypoint(181,30)),10,60,null));
        rejected(()->RouteEngine.build(1,from,to,List.of(new RouteEngine.Waypoint(121,31)),10,60,null));
        rejected(()->RouteEngine.build(1,from,to,via,.01,60,null));
        check(RouteEngine.legacy(from,from,10,60,20).points().size()==4);
        // Deterministic varied legs: normalized path sampling remains on exactly one original segment.
        var random=new Random(20261019);
        for(int trial=0;trial<100;trial++) {
            var p=RouteEngine.build(1,from,to,List.of(new RouteEngine.Waypoint(120.19+random.nextDouble()*.002,30.216+random.nextDouble()*.005)),10,60,null);
            for(int tick=0;tick<=p.durationSeconds();tick++) {
                var point=RouteEngine.at(p.points(),tick);
                boolean contained=false;
                for(int i=1;i<p.points().size();i++) {
                    var a=p.points().get(i-1);var b=p.points().get(i);
                    if(tick>=a.offsetSeconds()-1e-9 && tick<=b.offsetSeconds()+1e-9) contained=true;
                }
                check(contained && Double.isFinite(point.longitude()) && point.altitude()>=-1e-8 && point.altitude()<=60+1e-8);
            }
        }
        System.out.println("PASS: "+checks+" multi-waypoint route and continuous safety checks");
    }
}
