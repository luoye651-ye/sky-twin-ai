package com.ruoyi.skytwin;

import java.time.*;

/** Application JSON contract, not a GNSS receiver protocol or certified flight filter. */
public final class PositionRules {
    private PositionRules() {}
    public record Point(Instant time,double lon,double lat,double altitude) {}
    public static Instant time(String value) {
        // Explicit offset is mandatory. Milliseconds make HTTP, MySQL and replay agree.
        Instant result=OffsetDateTime.parse(value).toInstant();
        int year=LocalDateTime.ofInstant(result,ZoneOffset.UTC).getYear();
        if(year<1000 || year>9999) throw new IllegalArgumentException("采样时间超出存储范围");
        if(result.getNano()%1_000_000!=0) throw new IllegalArgumentException("采样时间最多保留毫秒");
        return result;
    }
    public static String verdict(Point point,Instant now,long sequence,long lastSequence,boolean fix,Point previous) {
        if(!Double.isFinite(point.lon()) || !Double.isFinite(point.lat()) || !Double.isFinite(point.altitude())
            || Math.abs(point.lon())>180 || Math.abs(point.lat())>90 || point.altitude() < -100 || point.altitude()>10000) return "invalid_coordinates";
        if(sequence<=lastSequence) return "out_of_order_sequence";
        if(point.time().isAfter(now.plusSeconds(5))) return "future_timestamp";
        if(point.time().isBefore(now.minusSeconds(30))) return "stale_timestamp";
        if(!fix) return "no_fix";
        if(previous!=null) {
            double seconds=Duration.between(previous.time(),point.time()).toMillis()/1000.0;
            if(seconds<=0) return "out_of_order_timestamp";
            double lat1=Math.toRadians(previous.lat()),lat2=Math.toRadians(point.lat());
            double h=Math.pow(Math.sin((lat2-lat1)/2),2)+Math.cos(lat1)*Math.cos(lat2)*Math.pow(Math.sin(Math.toRadians(point.lon()-previous.lon())/2),2);
            double horizontal=6371000*2*Math.asin(Math.min(1,Math.sqrt(h)));
            // Deliberately simple plausibility gate: 100 m/s horizontal, 30 m/s vertical + noise margins.
            if(horizontal>100*seconds+30 || Math.abs(point.altitude()-previous.altitude())>30*seconds+10) return "position_jump";
        }
        return "accepted";
    }
}
