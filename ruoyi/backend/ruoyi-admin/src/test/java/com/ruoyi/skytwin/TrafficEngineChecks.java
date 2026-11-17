package com.ruoyi.skytwin;
import java.util.*;
public class TrafficEngineChecks {
    static int checks;
    static void check(boolean ok,String name) { checks++;if(!ok) throw new AssertionError(name); }
    static AirspaceEngine.Point p(double x,double y,double z,double t) { return new AirspaceEngine.Point(120.2+x/96300,30.2+y/111195,z,t); }
    static TrafficEngine.Flight f(String id,long start,AirspaceEngine.Point...points) { return new TrafficEngine.Flight(id,id,"A-"+id,start,List.of(points)); }
    static boolean hit(TrafficEngine.Flight a,TrafficEngine.Flight b,long now) { return !TrafficEngine.conflicts(a,List.of(b),now).isEmpty(); }
    public static void main(String[] args) {
        var a=f("a",0,p(-1000,0,100,0),p(1000,0,100,10));
        var b=f("b",0,p(0,-1000,100,0),p(0,1000,100,10));
        check(hit(a,b,0),"same-height crossing");check(!hit(a,f("b",20,p(0,-1000,100,0),p(0,1000,100,10)),0),"different time");
        check(!hit(a,f("b",0,p(0,-1000,131,0),p(0,1000,131,10)),0),"vertical separation");
        check(hit(a,f("b",0,p(0,-1000,130,0),p(0,1000,130,10)),0),"inclusive vertical boundary");
        check(!hit(a,b,6),"past conflict not replayed");check(!hit(a,a,0),"self ignored");
        check(hit(f("fastA",0,p(-1000,0,100,0),p(1000,0,100,1)),f("fastB",0,p(0,-1000,100,0),p(0,1000,100,1)),0),"crossing between 1Hz samples");
        check(hit(f("up",0,p(0,0,0,0),p(0,0,200,10)),f("cross",0,p(-1000,0,100,0),p(1000,0,100,10)),0),"climb crossing");
        check(!hit(f("up",0,p(0,0,0,0),p(0,0,200,10)),f("late",0,p(-2000,0,100,0),p(0,0,100,10)),0),"horizontal and vertical closeness must coincide");
        check(hit(f("turn",0,p(-1000,0,100,0),p(0,0,100,5),p(0,1000,100,10)),b,0),"waypoint turning point");
        check(hit(f("land",0,p(0,0,100,0),p(0,0,0,10)),f("launch",10,p(0,0,0,0),p(0,0,100,10)),0),"shared endpoint instant guarded");
        check(!hit(f("land",0,p(0,0,100,0),p(0,0,0,10)),f("launch",11,p(0,0,0,0),p(0,0,100,10)),0),"separate endpoint times");
        check(hit(f("still",0,p(0,0,100,0),p(0,0,100,10)),f("near",0,p(105,0,100,0),p(105,0,100,10)),0),"explicit projection buffer");
        check(!hit(f("still",0,p(0,0,100,0),p(0,0,100,10)),f("far",0,p(120,0,100,0),p(120,0,100,10)),0),"outside protection band");
        var full=new ArrayList<TrafficEngine.Flight>();
        for(int i=0;i<200;i++) full.add(f("capacity"+i,0,p(0,0,100,0),p(0,0,100,10)));
        check(!TrafficEngine.hasLaunchCapacity("new",full),"manual start cannot create 201st occupancy");
        check(TrafficEngine.hasLaunchCapacity("capacity0",full),"own existing reservation is not double counted");
        full.remove(0);check(TrafficEngine.hasLaunchCapacity("new",full),"200th occupancy allowed");
        var random=new Random(19102026);
        for(int i=0;i<500;i++) {
            double x=random.nextDouble()*2000-1000,y=random.nextDouble()*2000-1000,z=random.nextDouble()*200;
            var c=f("c",random.nextInt(5),p(x,y,z,0),p(-x,-y,z,10));
            check(hit(a,c,0)==hit(c,a,0),"symmetry "+i);
            // Dense sampling is a one-way oracle: any sampled intrusion MUST be found continuously.
            boolean sampled=false;
            for(double t=c.departureTick();t<=10;t+=.01) {
                double ax=-1000+200*t,cx=x+( -2*x)*(t-c.departureTick())/10,cy=y+(-2*y)*(t-c.departureTick())/10;
                if(Math.hypot(ax-cx,cy)<98 && Math.abs(z-100)<29) { sampled=true;break; }
            }
            check(!sampled || hit(a,c,0),"no sampled false negatives "+i);
        }
        System.out.println("PASS: "+checks+" continuous multi-aircraft checks");
    }
}
