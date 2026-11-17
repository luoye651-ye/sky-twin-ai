package com.ruoyi.skytwin;

import java.time.LocalDateTime;
import java.util.*;
import static com.ruoyi.skytwin.DispatchOptimizer.*;

/** Dependency-free checks, including exhaustive optimum comparison on small random fleets. */
public final class DispatchOptimizerChecks {
    private static final LocalDateTime NOW=LocalDateTime.of(2026,10,18,12,0);
    private static int checks=0;
    private static void check(boolean value,String label) { if(!value) throw new AssertionError(label);checks++; }
    private static Job job(String id,String type,double payload,int priority) {
        return new Job(id,id,type,payload,"commute".equals(type)?2:0,60,120.19,30.2,null,priority,"created",true);
    }
    private static Vehicle aircraft(String id,String type,double capacity,double battery) {
        return new Vehicle(id,id,type,120.19,30.2,battery,capacity,"evtol".equals(type)?4:0,"idle");
    }
    private static long best;
    private static void exhaustive(List<Decision> jobs,int index,Set<String> used,int count,int priority,double cost) {
        if(index==jobs.size()) {
            long objective=-count*1_000_000_000L-priority*1_000_000L+Math.round(cost*100);
            best=Math.min(best,objective);return;
        }
        exhaustive(jobs,index+1,used,count,priority,cost);
        var job=jobs.get(index);
        for(var candidate:job.candidates()) if(candidate.eligible() && used.add(candidate.aircraftId())) {
            exhaustive(jobs,index+1,used,count+1,priority+job.priority(),cost+candidate.cost());used.remove(candidate.aircraftId());
        }
    }
    public static void main(String[] args) {
        // Greedy chooses the only cargo for a generic patrol and strands the delivery.
        var cargo=aircraft("A-cargo","cargo",20,100);
        var scout=new Vehicle("B-scout","scout","drone",120.191,30.2,95,2,0,"idle");
        var result=solve(List.of(job("1-patrol","environment",1,1),job("2-delivery","logistics",5,1)),List.of(cargo,scout),NOW);
        check(result.optimized().assignedCount()==2 && result.baseline().assignedCount()==1,"global reassignment improves coverage");
        check(result.assignments().stream().filter(x->x.taskId().equals("2-delivery")).findFirst().orElseThrow().aircraftId().equals("A-cargo"),"cargo reserved for delivery");
        var priority=solve(List.of(job("a","rescue",1,3),job("b","environment",1,1)),List.of(scout),NOW);
        check(priority.assignments().get(0).taskId().equals("a"),"higher priority wins scarce resource");
        var invalid=solve(List.of(job("d","logistics",30,1)),List.of(scout,aircraft("low","cargo",50,10)),NOW);
        check(invalid.assignments().isEmpty() && invalid.decisions().get(0).candidates().stream().allMatch(x->!x.reasons().isEmpty()),"infeasible resources explained");
        check(solve(List.of(),List.of(),NOW).assignments().isEmpty(),"empty graph terminates");
        var expired=new Job("late","late","logistics",1,0,60,120.19,30.2,NOW.plusSeconds(59),1,"created",true);
        check(solve(List.of(expired),List.of(cargo),NOW).assignments().isEmpty(),"late delivery rejected");
        check(constraintReasons("commute",60,1,5,null,aircraft("e","evtol",100,100),NOW).size()==1,"seat overflow rejected");
        check(constraintReasons("environment",60,1,0,null,aircraft("e","evtol",100,100),NOW).size()==1,"evtol excluded from drone missions");
        var disabled=new Job("off","off","rescue",1,0,60,120.19,30.2,null,1,"created",false);
        check(solve(List.of(disabled),List.of(cargo),NOW).assignments().isEmpty(),"disabled stations rejected");
        var random=new Random(521);
        for(int trial=0;trial<200;trial++) {
            var jobs=new ArrayList<Job>();var fleet=new ArrayList<Vehicle>();
            for(int i=0;i<4;i++) jobs.add(job("j"+i,List.of("environment","logistics","commute").get(random.nextInt(3)),random.nextInt(10),1+random.nextInt(3)));
            for(int i=0;i<4;i++) fleet.add(new Vehicle("v"+i,"v"+i,List.of("drone","cargo","evtol").get(random.nextInt(3)),120.19+random.nextDouble()*.1,30.2,20+random.nextInt(81),1+random.nextInt(20),4,"idle"));
            var solved=solve(jobs,fleet,NOW);best=Long.MAX_VALUE;
            exhaustive(solved.decisions(),0,new HashSet<>(),0,0,0);
            var metrics=solved.optimized();
            long actual=-metrics.assignedCount()*1_000_000_000L-metrics.priorityTotal()*1_000_000L+Math.round(metrics.totalCost()*100);
            check(actual==best,"matches exhaustive optimum trial "+trial);
            check(solved.assignments().stream().map(Assignment::aircraftId).distinct().count()==metrics.assignedCount(),"no repeated aircraft "+trial);
        }
        System.out.println("PASS "+checks+" optimizer checks; 200 exhaustive comparisons; benchmark optimized=2, nearest=1");
    }
}
