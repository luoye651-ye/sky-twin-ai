package com.ruoyi.skytwin;

import java.time.LocalDateTime;
import java.util.*;

/** Deterministic constrained fleet allocation, independent of HTTP and persistence. */
public final class DispatchOptimizer {
    public static final String VERSION = "fleet-mincost-v1";
    private DispatchOptimizer() {}
    public record Job(String id, String title, String type, double payload, int passengers,
        int durationSeconds, double longitude, double latitude, LocalDateTime deadlineAt,
        int priority, String status, boolean stationsEnabled) {}
    public record Vehicle(String id, String name, String type, double longitude, double latitude,
        double battery, double payloadCapacity, int seats, String status) {}
    public record Candidate(String aircraftId, String aircraftName, boolean eligible, List<String> reasons,
        double distanceMeters, double expectedEnergy, double remainingBattery, double distanceCost,
        double batteryCost, double capacityCost, double cost, double score) {}
    public record Assignment(String taskId, String taskTitle, int priority, String aircraftId,
        String aircraftName, double distanceMeters, double expectedEnergy, double remainingBattery,
        double cost, double score) {}
    public record Decision(String taskId, String taskTitle, String type, int priority,
        String aircraftId, String explanation, List<Candidate> candidates) {}
    public record Metrics(int assignedCount, int priorityTotal, double totalDistanceMeters,
        double totalExpectedEnergy, double totalCost) {}
    public record Result(String algorithm, List<Assignment> assignments, List<Decision> decisions,
        Metrics optimized, Metrics baseline, double calculationMs) {}

    /** Same hard constraints are called by the authoritative manual/batch assignment path. */
    public static List<String> constraintReasons(String type, double duration, double payload, int passengers,
        LocalDateTime deadline, Vehicle aircraft, LocalDateTime now) {
        var reasons = new ArrayList<String>();
        if (!Double.isFinite(aircraft.battery()) || !Double.isFinite(aircraft.payloadCapacity())
            || !Double.isFinite(duration) || !Double.isFinite(payload)) {
            reasons.add("资源或任务数值无效"); return reasons;
        }
        if (aircraft.battery() < Math.max(25, duration * .08 + 20)) reasons.add("电量不足，需保留至少20%仿真余量");
        if (aircraft.payloadCapacity() < payload) reasons.add("超过飞行器载重能力");
        if ("logistics".equals(type) && !"cargo".equals(aircraft.type())) reasons.add("物流配送必须分配货运无人机");
        if ("commute".equals(type)) {
            if (!"evtol".equals(aircraft.type()) || aircraft.seats() < passengers) reasons.add("需要座位充足的 eVTOL");
        } else if ("evtol".equals(aircraft.type())) reasons.add("该任务应分配无人机或货运无人机");
        if (deadline != null && now.plusSeconds((long)Math.ceil(duration)).isAfter(deadline))
            reasons.add("配送时限不足，预计仿真抵达时间晚于截止时间");
        return reasons;
    }

    public static Vehicle vehicle(Map<String,Object> row) {
        return new Vehicle(text(row,"id"),text(row,"name"),text(row,"type"),number(row,"longitude"),
            number(row,"latitude"),number(row,"battery"),number(row,"payloadCapacity"),
            (int)number(row,"seats"),text(row,"status"));
    }
    private static String text(Map<String,Object> row,String key) { return Objects.toString(row.get(key),""); }
    private static double number(Map<String,Object> row,String key) { return ((Number)row.get(key)).doubleValue(); }
    private static double round(double value) { return Math.round(value * 100.0) / 100.0; }
    private static boolean coordinate(double lon,double lat) {
        return Double.isFinite(lon) && Double.isFinite(lat) && Math.abs(lon)<=180 && Math.abs(lat)<=90;
    }
    private static double distance(Job job,Vehicle aircraft) {
        double lat1=Math.toRadians(job.latitude()),lat2=Math.toRadians(aircraft.latitude());
        double h=Math.pow(Math.sin((lat2-lat1)/2),2)+Math.cos(lat1)*Math.cos(lat2)
            *Math.pow(Math.sin(Math.toRadians(aircraft.longitude()-job.longitude())/2),2);
        return 6371000*2*Math.asin(Math.sqrt(Math.max(0,Math.min(1,h))));
    }
    private static Candidate evaluate(Job job,Vehicle aircraft,LocalDateTime now,List<String> airspaceReasons) {
        var reasons=constraintReasons(job.type(),job.durationSeconds(),job.payload(),job.passengers(),job.deadlineAt(),aircraft,now);
        reasons.addAll(airspaceReasons);
        if (!"created".equals(job.status())) reasons.add("任务已被分配或已结束");
        if (!job.stationsEnabled()) reasons.add("起终站点已停用、移除或类型不匹配");
        if ("terminal_positioning".equals(aircraft.status())) reasons.add("飞行器已启用终端定位，暂不参与任务仿真派机");
        else if (!"idle".equals(aircraft.status())) reasons.add("飞行器已被其他任务占用");
        boolean valid=coordinate(job.longitude(),job.latitude()) && coordinate(aircraft.longitude(),aircraft.latitude());
        if (!valid) reasons.add("起点或飞行器坐标无效");
        double distance=valid?distance(job,aircraft):0, energy=job.durationSeconds()*.08;
        double distanceCost=45*Math.min(distance/20000,1);
        double batteryCost=35*Math.max(0,Math.min(1,(100-aircraft.battery()+energy)/100));
        double capacityCost="commute".equals(job.type())
            ?20*(1-(double)job.passengers()/Math.max(1,aircraft.seats()))
            :job.payload()>0?20*(1-job.payload()/Math.max(.001,aircraft.payloadCapacity()))
            :"cargo".equals(aircraft.type())?20:0;
        capacityCost=Math.max(0,Math.min(20,capacityCost));
        double cost=round(distanceCost+batteryCost+capacityCost);
        return new Candidate(aircraft.id(),aircraft.name(),reasons.isEmpty(),List.copyOf(reasons),round(distance),
            round(energy),round(aircraft.battery()-energy),round(distanceCost),round(batteryCost),round(capacityCost),cost,round(100-cost));
    }
    private static Assignment assignment(Job job,Candidate candidate) {
        return new Assignment(job.id(),job.title(),job.priority(),candidate.aircraftId(),candidate.aircraftName(),
            candidate.distanceMeters(),candidate.expectedEnergy(),candidate.remainingBattery(),candidate.cost(),candidate.score());
    }
    private static Metrics metrics(List<Assignment> assignments) {
        return new Metrics(assignments.size(),assignments.stream().mapToInt(Assignment::priority).sum(),
            round(assignments.stream().mapToDouble(Assignment::distanceMeters).sum()),
            round(assignments.stream().mapToDouble(Assignment::expectedEnergy).sum()),
            round(assignments.stream().mapToDouble(Assignment::cost).sum()));
    }

    public static Result solve(List<Job> inputJobs,List<Vehicle> inputAircraft,LocalDateTime now) {
        return solve(inputJobs,inputAircraft,now,Map.of());
    }
    public static Result solve(List<Job> inputJobs,List<Vehicle> inputAircraft,LocalDateTime now,Map<String,List<String>> airspaceReasons) {
        long started=System.nanoTime();
        var jobs=inputJobs.stream().sorted(Comparator.comparingInt(Job::priority).reversed().thenComparing(Job::id)).toList();
        var aircraft=inputAircraft.stream().sorted(Comparator.comparing(Vehicle::id)).toList();
        int count=jobs.size(), vehicles=aircraft.size(), sink=count+vehicles+1;
        var graph=new ArrayList<List<Edge>>();
        for(int i=0;i<=sink;i++) graph.add(new ArrayList<>());
        var candidates=new ArrayList<List<Candidate>>();
        var matchingEdges=new Edge[count][vehicles];
        for(int i=0;i<count;i++) {
            // First maximize matching cardinality; then sum of selected task priorities;
            // finally cost. A priority unit exceeds all 20 assignments' possible costs.
            add(graph,0,1+i,1,(3L-jobs.get(i).priority())*1_000_000);
            var row=new ArrayList<Candidate>();
            for(int j=0;j<vehicles;j++) {
                var candidate=evaluate(jobs.get(i),aircraft.get(j),now,airspaceReasons.getOrDefault(jobs.get(i).id(),List.of())); row.add(candidate);
                if(candidate.eligible()) matchingEdges[i][j]=add(graph,1+i,1+count+j,1,Math.round(candidate.cost()*100));
            }
            candidates.add(row);
        }
        for(int j=0;j<vehicles;j++) add(graph,1+count+j,sink,1,0);
        // Successive shortest augmenting paths with reverse edges allow global reassignment.
        while(augment(graph,sink)) { /* one additional unique task/aircraft match */ }
        var assignments=new ArrayList<Assignment>();
        var decisions=new ArrayList<Decision>();
        var baseline=new ArrayList<Assignment>(); var used=new HashSet<String>();
        for(int i=0;i<count;i++) {
            var job=jobs.get(i); Candidate chosen=null;
            for(int j=0;j<vehicles;j++) if(matchingEdges[i][j]!=null && matchingEdges[i][j].capacity==0) chosen=candidates.get(i).get(j);
            if(chosen!=null) assignments.add(assignment(job,chosen));
            var ranked=candidates.get(i).stream().sorted(Comparator.comparing(Candidate::eligible).reversed()
                .thenComparingDouble(Candidate::cost).thenComparing(Candidate::aircraftId)).toList();
            String explanation=chosen!=null?"全局匹配已分配；兼顾任务覆盖、优先级与综合成本"
                :ranked.stream().anyMatch(Candidate::eligible)?"可用资源被同批其他任务分配，本任务等待下一轮"
                :"没有满足全部约束的飞行器，请查看候选排除原因";
            decisions.add(new Decision(job.id(),job.title(),job.type(),job.priority(),chosen==null?null:chosen.aircraftId(),explanation,ranked));
            candidates.get(i).stream().filter(c->c.eligible() && !used.contains(c.aircraftId()))
                .min(Comparator.comparingDouble(Candidate::distanceMeters).thenComparing(Candidate::aircraftId))
                .ifPresent(c->{baseline.add(assignment(job,c));used.add(c.aircraftId());});
        }
        return new Result(VERSION,assignments,decisions,metrics(assignments),metrics(baseline),round((System.nanoTime()-started)/1e6));
    }
    private static final class Edge {
        final int to,reverse; int capacity; final long cost;
        Edge(int to,int reverse,int capacity,long cost) { this.to=to;this.reverse=reverse;this.capacity=capacity;this.cost=cost; }
    }
    private static Edge add(List<List<Edge>> graph,int from,int to,int capacity,long cost) {
        var edge=new Edge(to,graph.get(to).size(),capacity,cost);
        var reverse=new Edge(from,graph.get(from).size(),0,-cost);
        graph.get(from).add(edge);graph.get(to).add(reverse);return edge;
    }
    private static boolean augment(List<List<Edge>> graph,int sink) {
        long[] distances=new long[graph.size()]; Arrays.fill(distances,Long.MAX_VALUE/4);distances[0]=0;
        int[] nodes=new int[graph.size()],edges=new int[graph.size()];Arrays.fill(nodes,-1);
        boolean[] queued=new boolean[graph.size()]; var queue=new ArrayDeque<Integer>();queue.add(0);queued[0]=true;
        while(!queue.isEmpty()) {
            int from=queue.remove();queued[from]=false;
            for(int i=0;i<graph.get(from).size();i++) {
                var edge=graph.get(from).get(i);
                if(edge.capacity>0 && distances[from]+edge.cost<distances[edge.to]) {
                    distances[edge.to]=distances[from]+edge.cost;nodes[edge.to]=from;edges[edge.to]=i;
                    if(!queued[edge.to]) {queue.add(edge.to);queued[edge.to]=true;}
                }
            }
        }
        if(nodes[sink]<0) return false;
        for(int node=sink;node!=0;node=nodes[node]) {
            var edge=graph.get(nodes[node]).get(edges[node]);edge.capacity--;graph.get(node).get(edge.reverse).capacity++;
        }
        return true;
    }
}
