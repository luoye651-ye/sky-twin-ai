package com.ruoyi.skytwin;
import java.util.*;

/** Bounded visibility graph of inflated rectangular exclusions. No buildings/terrain/real flight. */
public final class DetourPlanner {
    public record Rect(double west,double south,double east,double north){}
    static boolean crosses(RouteEngine.Waypoint a,RouteEngine.Waypoint b,Rect r){
        double low=0,high=1;double[] p={a.longitude(),a.latitude()},d={b.longitude()-a.longitude(),b.latitude()-a.latitude()},min={r.west(),r.south()},max={r.east(),r.north()};
        for(int k=0;k<2;k++){if(Math.abs(d[k])<1e-12){if(p[k]<min[k]||p[k]>max[k])return false;}else{double x=(min[k]-p[k])/d[k],y=(max[k]-p[k])/d[k];low=Math.max(low,Math.min(x,y));high=Math.min(high,Math.max(x,y));if(low>high)return false;}}
        return high>=0&&low<=1;
    }
    public static List<RouteEngine.Waypoint> segment(RouteEngine.Waypoint start,RouteEngine.Waypoint end,List<Rect> rectangles){
        if(rectangles.size()>30)throw new IllegalArgumentException("自动建议最多处理30个有效区域，请缩小区域配置");
        var nodes=new ArrayList<RouteEngine.Waypoint>(List.of(start,end));
        for(var r:rectangles){double m=.0006;for(double x:new double[]{r.west()-m,r.east()+m})for(double y:new double[]{r.south()-m,r.north()+m})if(Math.abs(x)<=180&&Math.abs(y)<=90)nodes.add(new RouteEngine.Waypoint(x,y));}
        int size=nodes.size();double[] costs=new double[size];int[] previous=new int[size];boolean[] used=new boolean[size];Arrays.fill(costs,Double.POSITIVE_INFINITY);Arrays.fill(previous,-1);costs[0]=0;
        for(int step=0;step<size;step++){
            int from=-1;for(int i=0;i<size;i++)if(!used[i]&&(from<0||costs[i]<costs[from]))from=i;
            if(from<0||!Double.isFinite(costs[from]))break;if(from==1)break;used[from]=true;
            for(int to=0;to<size;to++){
                if(used[to]||from==to)continue;var a=nodes.get(from);var b=nodes.get(to);boolean clear=true;
                for(var rect:rectangles)if(crosses(a,b,rect)){clear=false;break;}if(!clear)continue;
                double distance=EnvironmentRules.distance(a.longitude(),a.latitude(),b.longitude(),b.latitude());
                if(costs[from]+distance<costs[to]){costs[to]=costs[from]+distance;previous[to]=from;}
            }
        }
        if(previous[1]<0)throw new IllegalArgumentException("未找到可行候选路线；请检查起终点是否位于限制区内");
        var result=new ArrayList<RouteEngine.Waypoint>();int at=1;while(at!=0){result.add(nodes.get(at));at=previous[at];}Collections.reverse(result);return result;
    }
    public static List<RouteEngine.Waypoint> plan(List<RouteEngine.Waypoint> required,List<Rect> rectangles){
        var path=new ArrayList<RouteEngine.Waypoint>();for(int i=1;i<required.size();i++)path.addAll(segment(required.get(i-1),required.get(i),rectangles));
        if(!path.isEmpty())path.remove(path.size()-1);if(path.size()>24)throw new IllegalArgumentException("候选路线超过24个中间航点，请人工调整");return path;
    }
}
