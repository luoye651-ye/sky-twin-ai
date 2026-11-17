package com.ruoyi.skytwin;

import java.util.*;

/** One timed route model for planning, continuous airspace clipping and simulation. */
public final class RouteEngine {
    private RouteEngine() {}
    public record Waypoint(double longitude,double latitude) {}
    public record Plan(int revision,List<Waypoint> waypoints,List<AirspaceEngine.Point> points,
        double distanceMeters,int durationSeconds,double speed,double cruiseAltitude) {}
    public static double distance(Waypoint a,Waypoint b) {
        double lat1=Math.toRadians(a.latitude()),lat2=Math.toRadians(b.latitude());
        double h=Math.pow(Math.sin((lat2-lat1)/2),2)+Math.cos(lat1)*Math.cos(lat2)*Math.pow(Math.sin(Math.toRadians(b.longitude()-a.longitude())/2),2);
        return 6371000*2*Math.asin(Math.sqrt(Math.max(0,Math.min(1,h))));
    }
    private static void require(boolean ok,String message) { if(!ok) throw new IllegalArgumentException(message); }
    public static Plan legacy(Waypoint from,Waypoint to,double speed,double altitude,int duration) {
        // Historical stations may have moved since a terminal legacy task. Do not rewrite/revalidate old records.
        return new Plan(0,List.of(),AirspaceEngine.path(new AirspaceEngine.Flight("","",from.longitude(),from.latitude(),to.longitude(),to.latitude(),altitude,duration)),distance(from,to),duration,speed,altitude);
    }
    public static Plan build(int revision,Waypoint from,Waypoint to,List<Waypoint> via,double speed,double altitude,Integer legacyDuration) {
        require(via!=null && via.size()<=24,"最多24个中间航点");
        require(Double.isFinite(speed) && speed>0 && Double.isFinite(altitude) && altitude>=0 && altitude<=1000,"航线速度或巡航高度无效");
        var stops=new ArrayList<Waypoint>();stops.add(from);stops.addAll(via);stops.add(to);
        double length=0;var cumulative=new ArrayList<Double>();cumulative.add(0.0);
        for(int i=0;i<stops.size();i++) {
            var p=stops.get(i);
            require(Double.isFinite(p.longitude()) && Double.isFinite(p.latitude()) && Math.abs(p.longitude())<=180 && Math.abs(p.latitude())<=90,"航点必须为有限WGS84经纬度");
            if(i>0) { double leg=distance(stops.get(i-1),p);require(leg>=5,"相邻航点距离至少5米，请删除重复或过近的航点");length+=leg;cumulative.add(length); }
        }
        require(length>=10 && length<=20000,"总航程须在10米至20公里以内");
        // Cruise occupies 80% of simulation time; speed is physical nominal speed with 10x time scale.
        int duration=legacyDuration==null?(int)Math.max(20,Math.ceil(length/(speed*10*.8))):legacyDuration;
        require(duration>0 && duration<=600,"预计仿真时长不得超过600秒，请缩短航线");
        var path=new ArrayList<AirspaceEngine.Point>();path.add(new AirspaceEngine.Point(from.longitude(),from.latitude(),0,0));
        for(int i=0;i<stops.size();i++) { var p=stops.get(i);path.add(new AirspaceEngine.Point(p.longitude(),p.latitude(),altitude,duration*(.1+.8*cumulative.get(i)/length))); }
        path.add(new AirspaceEngine.Point(to.longitude(),to.latitude(),0,duration));
        return new Plan(revision,List.copyOf(via),List.copyOf(path),length,duration,speed,altitude);
    }
    public static AirspaceEngine.Point at(List<AirspaceEngine.Point> points,double seconds) {
        if(seconds<=0) return points.get(0);
        for(int i=1;i<points.size();i++) {
            var a=points.get(i-1);var b=points.get(i);
            if(seconds<=b.offsetSeconds()) {
                double f=Math.max(0,Math.min(1,(seconds-a.offsetSeconds())/(b.offsetSeconds()-a.offsetSeconds())));
                return new AirspaceEngine.Point(a.longitude()+(b.longitude()-a.longitude())*f,a.latitude()+(b.latitude()-a.latitude())*f,a.altitude()+(b.altitude()-a.altitude())*f,seconds);
            }
        }
        return points.get(points.size()-1);
    }
}
