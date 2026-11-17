package com.ruoyi.skytwin;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.*;

/** Continuous 4D rectangle clipping against the same three phases as SkyService.tick. */
public final class AirspaceEngine {
    private static final double EPS=1e-9;
    private AirspaceEngine() {}
    public record Zone(String id,String name,String type,double west,double south,double east,double north,
        double minAltitude,double maxAltitude,LocalDateTime startsAt,LocalDateTime endsAt,boolean enabled) {}
    public record Point(double longitude,double latitude,double altitude,double offsetSeconds) {}
    public record Flight(String taskId,String taskTitle,double startLongitude,double startLatitude,
        double endLongitude,double endLatitude,double cruiseAltitude,int durationSeconds) {}
    public record RuleSnapshot(double west,double south,double east,double north,double minAltitude,double maxAltitude,
        String startsAt,String endsAt) {}
    public record Violation(String zoneId,String zoneName,String type,String phase,Point from,Point to,
        String entersAt,String exitsAt,String reason,RuleSnapshot rule) {}
    public record Check(String taskId,String taskTitle,String departureAt,String checkedAt,long ruleRevision,
        boolean allowed,List<Point> route,List<Violation> violations) {}

    public static List<Point> path(Flight flight) {
        return List.of(new Point(flight.startLongitude(),flight.startLatitude(),0,0),
            new Point(flight.startLongitude(),flight.startLatitude(),flight.cruiseAltitude(),flight.durationSeconds()*.1),
            new Point(flight.endLongitude(),flight.endLatitude(),flight.cruiseAltitude(),flight.durationSeconds()*.9),
            new Point(flight.endLongitude(),flight.endLatitude(),0,flight.durationSeconds()));
    }
    public static Check check(Flight flight,List<Zone> zones,LocalDateTime departure,long revision,LocalDateTime now) {
        return checkPath(flight.taskId(),flight.taskTitle(),path(flight),zones,departure,revision,now);
    }
    public static Check checkPath(String taskId,String taskTitle,List<Point> route,List<Zone> zones,LocalDateTime departure,long revision,LocalDateTime now) {
        var violations=new ArrayList<Violation>();
        for(var zone:zones) {
            if(!zone.enabled()) continue;
            double begins=zone.startsAt()==null?Double.NEGATIVE_INFINITY:seconds(departure,zone.startsAt());
            double ends=zone.endsAt()==null?Double.POSITIVE_INFINITY:seconds(departure,zone.endsAt());
            for(int i=0;i<route.size()-1;i++) {
                var a=route.get(i);var b=route.get(i+1);double[] interval={0,1};
                if(!clip(a.longitude(),b.longitude(),zone.west(),zone.east(),interval)
                    || !clip(a.latitude(),b.latitude(),zone.south(),zone.north(),interval)
                    || !clip(a.offsetSeconds(),b.offsetSeconds(),begins,ends,interval)) continue;
                if("no_fly".equals(zone.type())) {
                    if(!clip(a.altitude(),b.altitude(),zone.minAltitude(),zone.maxAltitude(),interval)) continue;
                } else {
                    // A ceiling allows equality; only strictly higher points violate it.
                    if(Math.max(a.altitude(),b.altitude())<=zone.maxAltitude()+EPS
                        || !clip(a.altitude(),b.altitude(),zone.maxAltitude(),Double.POSITIVE_INFINITY,interval)) continue;
                }
                var from=lerp(a,b,interval[0]);var to=lerp(a,b,interval[1]);
                // Transition instants belong to the following phase (last phase includes touchdown).
                if(i<route.size()-2 && interval[0]>=1) continue;
                // Active period is [startsAt, endsAt). Spatial boundary is inclusive.
                if(from.offsetSeconds()>=ends-EPS || to.offsetSeconds()<begins-EPS) continue;
                if("height_limit".equals(zone.type()) && Math.max(from.altitude(),to.altitude())<=zone.maxAltitude()+EPS) continue;
                String reason="no_fly".equals(zone.type())?"航线进入禁飞区「"+zone.name()+"」":"航线超过「"+zone.name()+"」限高 "+zone.maxAltitude()+" m";
                violations.add(new Violation(zone.id(),zone.name(),zone.type(),i==0?"takeoff":i==route.size()-2?"landing":"cruise",
                    from,to,time(departure,from.offsetSeconds()),time(departure,to.offsetSeconds()),reason,
                    new RuleSnapshot(zone.west(),zone.south(),zone.east(),zone.north(),zone.minAltitude(),zone.maxAltitude(),
                        zone.startsAt()==null?null:zone.startsAt().toString(),zone.endsAt()==null?null:zone.endsAt().toString())));
            }
        }
        return new Check(taskId,taskTitle,departure.toString(),now.toString(),revision,violations.isEmpty(),route,violations);
    }
    private static double seconds(LocalDateTime from,LocalDateTime to) { var duration=Duration.between(from,to);return duration.getSeconds()+duration.getNano()/1e9; }
    private static String time(LocalDateTime start,double seconds) { return start.plusNanos(Math.round(seconds*1e9)).toString(); }
    private static Point lerp(Point a,Point b,double t) {
        return new Point(a.longitude()+(b.longitude()-a.longitude())*t,a.latitude()+(b.latitude()-a.latitude())*t,
            a.altitude()+(b.altitude()-a.altitude())*t,a.offsetSeconds()+(b.offsetSeconds()-a.offsetSeconds())*t);
    }
    private static boolean clip(double a,double b,double min,double max,double[] interval) {
        double delta=b-a;
        if(Math.abs(delta)<EPS) return a>=min-EPS && a<=max+EPS;
        double first=(min-a)/delta,second=(max-a)/delta;
        interval[0]=Math.max(interval[0],Math.min(first,second));interval[1]=Math.min(interval[1],Math.max(first,second));
        return interval[0]<=interval[1]+EPS;
    }
}
