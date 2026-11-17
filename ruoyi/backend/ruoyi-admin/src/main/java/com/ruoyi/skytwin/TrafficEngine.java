package com.ruoyi.skytwin;

import java.util.*;

/** Simulation-only continuous segment/segment separation, NOT a certified DAA system. */
public final class TrafficEngine {
    private TrafficEngine() {}
    public static final double HORIZONTAL_METERS=100, PROJECTION_BUFFER_METERS=10, VERTICAL_METERS=30;
    public record Flight(String taskId,String title,String aircraftId,long departureTick,List<AirspaceEngine.Point> points) {}
    public record Conflict(String taskId,String otherTaskId,String otherTitle,String otherAircraftId,
        double entersTick,double exitsTick,double longitude,double latitude,double altitude,
        double horizontalMeters,double verticalMeters) {}
    public static boolean hasLaunchCapacity(String taskId,List<Flight> others) {
        return others.stream().filter(x->!x.taskId().equals(taskId)).count()<200;
    }
    private static double[] position(AirspaceEngine.Point a,AirspaceEngine.Point b,double t) {
        double f=Math.max(0,Math.min(1,(t-a.offsetSeconds())/(b.offsetSeconds()-a.offsetSeconds())));
        return new double[]{a.longitude()+(b.longitude()-a.longitude())*f,a.latitude()+(b.latitude()-a.latitude())*f,a.altitude()+(b.altitude()-a.altitude())*f};
    }
    public static List<Conflict> conflicts(Flight flight,List<Flight> others,long nowTick) {
        var result=new ArrayList<Conflict>();
        for(var other:others) {
            if(other.taskId().equals(flight.taskId())) continue;
            Conflict first=null;
            for(int i=1;i<flight.points().size();i++) for(int j=1;j<other.points().size();j++) {
                var a=flight.points().get(i-1);var b=flight.points().get(i);
                var c=other.points().get(j-1);var d=other.points().get(j);
                double start=Math.max(nowTick,Math.max(flight.departureTick()+a.offsetSeconds(),other.departureTick()+c.offsetSeconds()));
                double end=Math.min(flight.departureTick()+b.offsetSeconds(),other.departureTick()+d.offsetSeconds());
                if(end<start) continue;
                var p=position(a,b,start-flight.departureTick());var q=position(c,d,start-other.departureTick());
                var pe=position(a,b,end-flight.departureTick());var qe=position(c,d,end-other.departureTick());
                double span=end-start;
                double[] interval={0,span};
                double z=p[2]-q[2],vz=span==0?0:((pe[2]-qe[2])-z)/span;
                if(!linear(z,vz,-VERTICAL_METERS,VERTICAL_METERS,interval)) continue;
                // Local WGS84 approximation with an explicit 10m guard band; intended for urban demo routes.
                double k=Math.PI/180*6371000,cos=Math.cos(Math.toRadians((p[1]+q[1]+pe[1]+qe[1])/4));
                double x=(p[0]-q[0])*k*cos,y=(p[1]-q[1])*k;
                double vx=span==0?0:((pe[0]-qe[0])*k*cos-x)/span,vy=span==0?0:((pe[1]-qe[1])*k-y)/span;
                double aa=vx*vx+vy*vy,bb=2*(x*vx+y*vy),cc=x*x+y*y-Math.pow(HORIZONTAL_METERS+PROJECTION_BUFFER_METERS,2);
                if(aa<1e-18) { if(cc>1e-7) continue; }
                else {
                    double disc=bb*bb-4*aa*cc;if(disc< -1e-7) continue;
                    double root=Math.sqrt(Math.max(0,disc));
                    interval[0]=Math.max(interval[0],(-bb-root)/(2*aa));interval[1]=Math.min(interval[1],(-bb+root)/(2*aa));
                }
                if(interval[0]>interval[1]+1e-8) continue;
                double t=Math.max(0,interval[0]);
                double f=span==0?0:t/span;
                var hit=new Conflict(flight.taskId(),other.taskId(),other.title(),other.aircraftId(),start+t,start+Math.max(t,interval[1]),
                    p[0]+(pe[0]-p[0])*f,p[1]+(pe[1]-p[1])*f,p[2]+(pe[2]-p[2])*f,
                    Math.hypot(x+vx*t,y+vy*t),Math.abs(z+vz*t));
                if(first==null || hit.entersTick()<first.entersTick()) first=hit;
            }
            if(first!=null) result.add(first);
        }
        result.sort(Comparator.comparingDouble(Conflict::entersTick).thenComparing(Conflict::otherTaskId));return result;
    }
    private static boolean linear(double value,double speed,double min,double max,double[] interval) {
        if(Math.abs(speed)<1e-12) return value>=min-1e-9 && value<=max+1e-9;
        double a=(min-value)/speed,b=(max-value)/speed;
        interval[0]=Math.max(interval[0],Math.min(a,b));interval[1]=Math.min(interval[1],Math.max(a,b));
        return interval[0]<=interval[1]+1e-9;
    }
}
