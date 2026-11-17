package com.ruoyi.skytwin;
import java.time.Instant;
import java.util.List;
/** Rules only; no image classification or trained model is implied. */
public final class EnvironmentRules {
    private EnvironmentRules() {}
    public static void coordinate(double lon,double lat) {
        if(!Double.isFinite(lon) || !Double.isFinite(lat) || Math.abs(lon)>180 || Math.abs(lat)>90) throw new IllegalArgumentException("位置必须是有效WGS84坐标");
    }
    public static void observed(Instant value,Instant now) {
        if(value.isAfter(now.plusSeconds(300)) || value.isBefore(now.minusSeconds(365L*86400))) throw new IllegalArgumentException("采集时间应在过去365天至未来5分钟内");
    }
    public static void box(double x,double y,double width,double height) {
        if(!Double.isFinite(x) || !Double.isFinite(y) || !Double.isFinite(width) || !Double.isFinite(height)
            || x<0 || y<0 || width<=0 || height<=0 || x+width>1+1e-9 || y+height>1+1e-9) throw new IllegalArgumentException("标注框必须完整位于图片内，坐标为0～1比例");
    }
    public static int priority(String severity) { return "high".equals(severity)?3:"medium".equals(severity)?2:1; }
    public static double distance(double lon1,double lat1,double lon2,double lat2) {
        double a=Math.toRadians(lat1),b=Math.toRadians(lat2);
        double h=Math.pow(Math.sin((b-a)/2),2)+Math.cos(a)*Math.cos(b)*Math.pow(Math.sin(Math.toRadians(lon2-lon1)/2),2);
        return 6371000*2*Math.asin(Math.sqrt(Math.min(1,Math.max(0,h))));
    }
    public static boolean visits(List<AirspaceEngine.Point> points,double lon,double lat) {
        return points.stream().anyMatch(p->p.altitude()>0 && distance(lon,lat,p.longitude(),p.latitude())<=10);
    }
}
