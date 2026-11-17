package com.ruoyi.skytwin;
import java.time.*;
public class NmeaGgaChecks {
    private static int checks;
    private static void check(boolean ok) { checks++;if(!ok) throw new AssertionError("NMEA check "+checks); }
    private static String frame(String body) { int sum=0;for(char c:body.toCharArray())sum^=c;return "$"+body+"*"+String.format("%02X",sum); }
    private static String body="GBGGA,153045.123,3012.90000,N,12011.40000,E,1,12,0.9,252.0,M,0.0,M,,";
    private static NmeaGga.Fix parse(String b) {return NmeaGga.decode(frame(b),"2026-10-22",12);}
    private static void rejects(String b) {boolean rejected=false;try{parse(b);}catch(RuntimeException e){rejected=true;}check(rejected);}
    public static void main(String[] args) {
        var fix=parse(body);
        check(fix.talker().equals("GB") && fix.constellation().equals("BeiDou"));
        check(Math.abs(fix.longitude()-120.19)<1e-9 && Math.abs(fix.latitude()-30.215)<1e-9);
        check(fix.relativeAltitude()==240 && fix.altitudeMsl()==252 && fix.takeoffAltitudeMsl()==12);
        check(fix.sampledAt().equals("2026-10-22T15:30:45.123Z"));
        check(fix.satellites()==12 && fix.hdop()==.9 && fix.fixValid());
        check(parse(body.replace("GBGGA","GNGGA")).constellation().equals("GNSS（星座未确定）"));
        check(parse(body.replace("GBGGA","GPGGA")).constellation().equals("GPS"));
        check(!parse(body.replace(",1,12,",",0,00,")).fixValid());
        check(!parse(body.replace(",1,12,",",1,03,")).fixValid());
        var south=parse(body.replace(",N,",",S,").replace(",E,",",W,"));
        check(south.longitude()<0 && south.latitude()<0);
        rejects(body.replace("3012.90000","3060.00000"));
        rejects(body.replace("12011.40000","18000.00001"));
        rejects(body.replace(",N,",",E,"));
        rejects(body.replace("153045.123","240000"));
        rejects(body.replace("153045.123","235960"));
        rejects(body.replace("153045.123","153045.1234"));
        rejects(body.replace(",0.9,",",NaN,"));
        rejects(body.replace(",252.0,",",Infinity,"));
        rejects(body.replace(",1,12,",",6,12,"));
        rejects(body.replace("GBGGA","GBRMC"));
        rejects(body.replace(",M,0.0",",F,0.0"));
        rejects(body+",extra");
        for(String date:new String[]{"2026-02-30","2026-10-22T00:00:00Z","0999-01-01"}) {
            boolean rejected=false;try{NmeaGga.decode(frame(body),date,12);}catch(RuntimeException e){rejected=true;}check(rejected);
        }
        for(String raw:new String[]{frame(body)+"X",frame(body).replace("252.0","253.0"),frame(body)+"\n"+frame(body),"$GBGGA,no-checksum"}) {
            boolean rejected=false;try{NmeaGga.decode(raw,"2026-10-22",12);}catch(RuntimeException e){rejected=true;}check(rejected);
        }
        boolean rejected=false;try{NmeaGga.decode(frame(body),"2026-10-22",Double.NaN);}catch(RuntimeException e){rejected=true;}check(rejected);
        var now=Instant.parse(fix.sampledAt());
        var point=new PositionRules.Point(now,fix.longitude(),fix.latitude(),fix.relativeAltitude());
        check(PositionRules.verdict(point,now,0,-1,fix.fixValid(),null).equals("accepted"));
        check(PositionRules.verdict(point,now.plusSeconds(31),0,-1,true,null).equals("stale_timestamp"));
        check(PositionRules.verdict(point,now,0,-1,false,null).equals("no_fix"));
        System.out.println("PASS: "+checks+" NMEA adapter and positioning boundary checks");
    }
}
