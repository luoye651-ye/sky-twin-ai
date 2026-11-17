import com.ruoyi.skytwin.DispatchOptimizer;
import static com.ruoyi.skytwin.DispatchOptimizer.*;
import java.time.LocalDateTime;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** Deterministic offline evidence. No HTTP, database, model API or flight operation. */
public final class SummaryBenchmark {
    private static final LocalDateTime NOW=LocalDateTime.of(2026,10,18,12,0);
    private static long exactBest;
    private static Job job(String id,String type,double payload,int priority) {
        return new Job(id,id,type,payload,"commute".equals(type)?2:0,60,120.19,30.2,null,priority,"created",true);
    }
    private static Vehicle vehicle(String id,String type,double capacity,double battery) {
        return new Vehicle(id,id,type,120.19,30.2,battery,capacity,"evtol".equals(type)?4:0,"idle");
    }
    private static long objective(int count,int priority,double cost) {
        return -count*1_000_000_000L-priority*1_000_000L+Math.round(cost*100);
    }
    private static long objective(Metrics value) {
        return objective(value.assignedCount(),value.priorityTotal(),value.totalCost());
    }
    private static void exhaustive(List<Decision> jobs,int index,Set<String> used,int count,int priority,double cost) {
        if(index==jobs.size()) {
            exactBest=Math.min(exactBest,objective(count,priority,cost)); return;
        }
        exhaustive(jobs,index+1,used,count,priority,cost);
        Decision task=jobs.get(index);
        for(Candidate c:task.candidates()) if(c.eligible() && used.add(c.aircraftId())) {
            exhaustive(jobs,index+1,used,count+1,priority+task.priority(),cost+c.cost());
            used.remove(c.aircraftId());
        }
    }
    private record Probe(String name,String type,double payload,int seats,LocalDateTime deadline,Vehicle aircraft) {}
    private static String csv(Object value) { return "\""+String.valueOf(value).replace("\"","\"\"")+"\""; }
    private static String probeLine(String group,Probe p,List<String> reasons) {
        return String.join(",",csv(group),csv(p.name()),csv(p.type()),"60",csv(p.payload()),csv(p.seats()),
            csv(p.deadline()==null?"":p.deadline()),csv(p.aircraft().type()),csv(p.aircraft().status()),
            csv(p.aircraft().battery()),csv(p.aircraft().payloadCapacity()),csv(p.aircraft().seats()),
            csv("idle".equals(p.aircraft().status())),csv(reasons.isEmpty()),csv(String.join(" | ",reasons)))+"\n";
    }
    public static void main(String[] args) throws Exception {
        if(args.length!=1) throw new IllegalArgumentException("Usage: SummaryBenchmark OUTPUT_DIRECTORY");
        Path output=Path.of(args[0]); Files.createDirectories(output);
        Vehicle cargo=vehicle("A-cargo","cargo",20,100);
        Vehicle scout=new Vehicle("B-scout","scout","drone",120.191,30.2,95,2,0,"idle");
        Result fixed=solve(List.of(job("1-patrol","environment",1,1),job("2-delivery","logistics",5,1)),List.of(cargo,scout),NOW);
        if(fixed.optimized().assignedCount()!=2 || fixed.baseline().assignedCount()!=1) throw new AssertionError("fixed benchmark");
        Random random=new Random(521);
        int optimizedExact=0,nearestExact=0,optimizedAssigned=0,nearestAssigned=0;
        StringBuilder trials=new StringBuilder("trial,optimized_assigned,nearest_assigned,optimized_priority,nearest_priority,optimized_cost,nearest_cost,exhaustive_objective,optimized_objective,nearest_objective,optimized_exact,nearest_exact\n");
        for(int trial=0;trial<200;trial++) {
            List<Job> jobs=new ArrayList<>();List<Vehicle> fleet=new ArrayList<>();
            for(int i=0;i<4;i++) jobs.add(job("j"+i,List.of("environment","logistics","commute").get(random.nextInt(3)),random.nextInt(10),1+random.nextInt(3)));
            for(int i=0;i<4;i++) fleet.add(new Vehicle("v"+i,"v"+i,List.of("drone","cargo","evtol").get(random.nextInt(3)),120.19+random.nextDouble()*.1,30.2,20+random.nextInt(81),1+random.nextInt(20),4,"idle"));
            Result result=solve(jobs,fleet,NOW);
            exactBest=Long.MAX_VALUE;
            exhaustive(result.decisions(),0,new HashSet<>(),0,0,0);
            Metrics opt=result.optimized(), near=result.baseline();
            boolean optExact=objective(opt)==exactBest, nearExact=objective(near)==exactBest;
            if(optExact) optimizedExact++;
            if(nearExact) nearestExact++;
            optimizedAssigned+=opt.assignedCount();
            nearestAssigned+=near.assignedCount();
            trials.append(String.format(Locale.ROOT,"%d,%d,%d,%d,%d,%.2f,%.2f,%d,%d,%d,%s,%s%n",trial+1,opt.assignedCount(),near.assignedCount(),opt.priorityTotal(),near.priorityTotal(),opt.totalCost(),near.totalCost(),exactBest,objective(opt),objective(near),optExact,nearExact));
        }
        List<Probe> invalid=List.of(
            new Probe("battery","logistics",1,0,null,vehicle("c","cargo",20,10)),
            new Probe("payload","logistics",5,0,null,vehicle("c","cargo",2,100)),
            new Probe("type","logistics",1,0,null,vehicle("d","drone",2,100)),
            new Probe("seats","commute",1,5,null,vehicle("e","evtol",100,100)),
            new Probe("mission","environment",1,0,null,vehicle("e","evtol",100,100)),
            new Probe("deadline","logistics",1,0,NOW.plusSeconds(59),cargo),
            new Probe("nonfinite_battery","logistics",1,0,null,vehicle("c","cargo",20,Double.NaN)),
            new Probe("nonfinite_capacity","logistics",1,0,null,vehicle("c","cargo",Double.POSITIVE_INFINITY,100))
        );
        List<Probe> valid=List.of(
            new Probe("cargo","logistics",5,0,null,cargo),
            new Probe("patrol","environment",1,0,null,scout),
            new Probe("commute","commute",1,2,null,vehicle("e","evtol",100,100)),
            new Probe("rescue","rescue",1,0,null,cargo)
        );
        StringBuilder probes=new StringBuilder("group,probe,task_type,duration_seconds,payload_kg,passengers,deadline,aircraft_type,aircraft_status,battery_percent,capacity_kg,seats,idle_only_accepted,full_constraint_accepted,reasons\n");
        int optimizerFalseAccepts=0,idleOnlyFalseAccepts=0,validAccepted=0;
        for(Probe p:invalid) {
            List<String> reasons=constraintReasons(p.type(),60,p.payload(),p.seats(),p.deadline(),p.aircraft(),NOW);
            if(reasons.isEmpty()) optimizerFalseAccepts++;
            if("idle".equals(p.aircraft().status())) idleOnlyFalseAccepts++;
            probes.append(probeLine("invalid",p,reasons));
        }
        for(Probe p:valid) {
            List<String> reasons=constraintReasons(p.type(),60,p.payload(),p.seats(),p.deadline(),p.aircraft(),NOW);
            if(reasons.isEmpty()) validAccepted++;
            probes.append(probeLine("valid",p,reasons));
        }
        if(optimizedExact!=200 || nearestExact!=115 || optimizedAssigned!=506 || nearestAssigned!=487)
            throw new AssertionError("Original summary-offline-v1 metrics changed; inspect source or protocol before updating report");
        if(optimizerFalseAccepts!=0 || idleOnlyFalseAccepts!=8 || validAccepted!=4) throw new AssertionError("candidate checks");
        String json=String.format(Locale.ROOT,"""
            {
              "protocol": "summary-offline-v1",
              "simulationTime": "2026-10-18T12:00:00",
              "randomSeed": 521,
              "randomCases": 200,
              "jobsPerCase": 4,
              "aircraftPerCase": 4,
              "optimizedExactMatches": %d,
              "nearestExactMatches": %d,
              "optimizedAssignedSum": %d,
              "nearestAssignedSum": %d,
              "fixedOptimizedAssignments": 2,
              "fixedNearestAssignments": 1,
              "invalidCandidateCases": 8,
              "optimizerFalseAccepts": %d,
              "idleOnlyFalseAccepts": %d,
              "validCandidateCases": 4,
              "validAccepted": %d,
              "baseline1": "same hard constraints, priority then nearest greedy",
              "baseline2": "ablation: idle-status-only admission, not a historical or competing product",
              "scope": "deterministic synthetic offline assignment tests, not real flight or industry-wide performance"
            }
            """,optimizedExact,nearestExact,optimizedAssigned,nearestAssigned,optimizerFalseAccepts,idleOnlyFalseAccepts,validAccepted);
        Files.writeString(output.resolve("benchmark.json"),json,StandardCharsets.UTF_8);
        Files.writeString(output.resolve("random-cases.csv"),trials,StandardCharsets.UTF_8);
        Files.writeString(output.resolve("candidate-cases.csv"),probes,StandardCharsets.UTF_8);
        System.out.println(json);
    }
}
