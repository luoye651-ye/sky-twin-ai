package com.ruoyi.skytwin;

import java.time.*;
import java.util.Set;

/** Bounded GGA adapter for the simulation endpoint, not proof of a physical receiver. */
public final class NmeaGga {
    private NmeaGga() {}
    public record Fix(String talker, String constellation, String sampledAt, double longitude,
        double latitude, double altitudeMsl, double takeoffAltitudeMsl, double relativeAltitude,
        int quality, int satellites, double hdop, boolean fixValid) {}

    public static Fix decode(String sentence, String utcDate, double takeoffAltitudeMsl) {
        require(sentence != null && sentence.length() <= 160, "报文不能为空且最多160字符");
        String raw=sentence.strip();
        require(raw.matches("\\$[\\x20-\\x7e]+\\*[0-9A-Fa-f]{2}"), "需要单行NMEA报文和两位校验和");
        int star=raw.lastIndexOf('*'), checksum=0;
        for(int i=1;i<star;i++) checksum^=raw.charAt(i);
        require(checksum==Integer.parseInt(raw.substring(star+1),16), "NMEA校验和不匹配");
        String[] f=raw.substring(1,star).split(",",-1);
        require(f.length==15 && Set.of("GBGGA","GNGGA","GPGGA").contains(f[0]), "演示适配器仅支持GB/GN/GP GGA的15个字段");
        require(utcDate!=null && utcDate.matches("\\d{4}-\\d{2}-\\d{2}"), "GGA不含日期，必须显式提供UTC日期");
        LocalDate date=LocalDate.parse(utcDate);
        require(date.getYear()>=1000, "UTC日期年份须在1000至9999之间");
        require(f[1].matches("\\d{6}(\\.\\d{1,3})?"), "UTC时分秒格式无效，最多保留毫秒");
        int hour=Integer.parseInt(f[1].substring(0,2)), minute=Integer.parseInt(f[1].substring(2,4)), second=Integer.parseInt(f[1].substring(4,6));
        String fraction=f[1].length()>6?f[1].substring(7):"";
        int millis=fraction.isEmpty()?0:Integer.parseInt((fraction+"000").substring(0,3));
        String sampled=LocalDateTime.of(date,LocalTime.of(hour,minute,second,millis*1000000)).toInstant(ZoneOffset.UTC).toString();
        double latitude=coordinate(f[2],f[3],true), longitude=coordinate(f[4],f[5],false);
        require(f[6].matches("[01245]"), "仅支持无定位、单点、差分、RTK固定/浮点质量码；不支持推算定位");
        int quality=Integer.parseInt(f[6]);
        require(f[7].matches("\\d{1,2}"), "卫星数字段无效");
        int satellites=Integer.parseInt(f[7]);
        double hdop=number(f[8],"HDOP");
        require(hdop>=0 && hdop<=99.9,"HDOP超出演示适配范围");
        double msl=number(f[9],"MSL高度");
        require("M".equals(f[10]) && "M".equals(f[12]),"GGA高度单位必须为米");
        if(!f[11].isEmpty()) number(f[11],"大地水准面差距");
        require(Double.isFinite(takeoffAltitudeMsl) && takeoffAltitudeMsl>=-1000 && takeoffAltitudeMsl<=10000,"起飞点MSL基准无效");
        double relative=msl-takeoffAltitudeMsl;
        require(relative>=-100 && relative<=10000,"换算后相对高度超出定位接口范围");
        String talker=f[0].substring(0,2);
        return new Fix(talker,"GB".equals(talker)?"BeiDou":"GN".equals(talker)?"GNSS（星座未确定）":"GPS",
            sampled,longitude,latitude,msl,takeoffAltitudeMsl,relative,quality,satellites,hdop,
            quality!=0 && satellites>=4 && hdop>0);
    }
    private static double coordinate(String text,String hemisphere,boolean latitude) {
        int degreesDigits=latitude?2:3;
        require(text.matches("\\d{"+(degreesDigits+2)+"}(\\.\\d{1,8})?"),"经纬度须为度分格式");
        double degrees=Double.parseDouble(text.substring(0,degreesDigits)), minutes=Double.parseDouble(text.substring(degreesDigits));
        int limit=latitude?90:180;
        require(minutes<60 && degrees<=limit && (degrees<limit || minutes==0),"经纬度度分超出范围");
        require((latitude?Set.of("N","S"):Set.of("E","W")).contains(hemisphere),"经纬度半球标识无效");
        return (degrees+minutes/60)*(Set.of("S","W").contains(hemisphere)?-1:1);
    }
    private static double number(String text,String field) {
        require(text.matches("[+-]?\\d+(\\.\\d+)?"),field+"须为有限十进制数");
        double value=Double.parseDouble(text);require(Double.isFinite(value),field+"须为有限数值");return value;
    }
    private static void require(boolean condition,String message) { if(!condition) throw new IllegalArgumentException(message); }
}
