package com.ruoyi.skytwin;
import java.util.*;
import java.time.Instant;
import java.io.ByteArrayOutputStream;
import java.awt.image.BufferedImage;
import javax.imageio.ImageIO;
public class EnvironmentRulesChecks {
    static int checks;
    static void check(boolean ok,String name) { checks++;if(!ok) throw new AssertionError(name); }
    static void reject(Runnable f,String name) { boolean failed=false;try { f.run(); } catch(IllegalArgumentException e) { failed=true; }check(failed,name); }
    public static void main(String[] args) throws Exception {
        EnvironmentRules.coordinate(120.2,30.2);EnvironmentRules.coordinate(-180,90);
        reject(()->EnvironmentRules.coordinate(Double.NaN,30),"NaN longitude");reject(()->EnvironmentRules.coordinate(120,Double.POSITIVE_INFINITY),"infinite latitude");reject(()->EnvironmentRules.coordinate(181,30),"range");
        EnvironmentRules.box(0,0,1,1);EnvironmentRules.box(.2,.2,.5,.5);
        reject(()->EnvironmentRules.box(.7,0,.5,.5),"box outside image");reject(()->EnvironmentRules.box(0,0,0,.5),"empty box");reject(()->EnvironmentRules.box(Double.NaN,0,.5,.5),"NaN box");
        var now=Instant.parse("2026-10-19T10:00:00Z");EnvironmentRules.observed(now,now);EnvironmentRules.observed(now.plusSeconds(300),now);
        reject(()->EnvironmentRules.observed(now.plusSeconds(301),now),"future timestamp");reject(()->EnvironmentRules.observed(now.minusSeconds(366L*86400),now),"old timestamp");
        check(EnvironmentRules.priority("high")==3 && EnvironmentRules.priority("medium")==2 && EnvironmentRules.priority("low")==1,"severity priority floors");
        check(EnvironmentRules.visits(List.of(new AirspaceEngine.Point(120.2,30.2,80,5)),120.2,30.2),"actual aerial visit");
        check(!EnvironmentRules.visits(List.of(new AirspaceEngine.Point(120.2,30.2,0,5)),120.2,30.2),"ground does not count as reconnaissance");
        check(!EnvironmentRules.visits(List.of(new AirspaceEngine.Point(120.3,30.2,80,5)),120.2,30.2),"distant route does not visit event");
        var image=new BufferedImage(20,12,BufferedImage.TYPE_INT_RGB);image.setRGB(5,5,0xabcdef);
        var bytes=new ByteArrayOutputStream();ImageIO.write(image,"png",bytes);
        var parsed=EnvironmentImage.read(bytes.toByteArray(),"../../evidence.png");
        check(parsed.width()==20 && parsed.height()==12 && parsed.mime().equals("image/png"),"decode actual bounded PNG");
        check(Arrays.equals(parsed.bytes(),bytes.toByteArray()) && parsed.sha256().length()==64,"preserve original evidence and SHA256");
        check(parsed.originalName().equals("evidence.png"),"filename is display-only basename");
        reject(()->EnvironmentImage.read("<svg></svg>".getBytes(),"photo.png"),"fake PNG / SVG refused");
        reject(()->EnvironmentImage.read(new byte[0],"empty.png"),"empty image");reject(()->EnvironmentImage.read(new byte[2*1024*1024+1],"large.png"),"byte limit");
        var tooWide=new ByteArrayOutputStream();ImageIO.write(new BufferedImage(4097,1,BufferedImage.TYPE_INT_RGB),"png",tooWide);
        reject(()->EnvironmentImage.read(tooWide.toByteArray(),"wide.png"),"pixel dimension checked before decode");
        var random=new Random(19102026);
        for(int i=0;i<500;i++) {
            double x=random.nextDouble(),y=random.nextDouble(),w=(1-x)*random.nextDouble()+1e-12,h=(1-y)*random.nextDouble()+1e-12;
            EnvironmentRules.box(x,y,w,h);check(true,"valid normalized box "+i);
            double lon=119+random.nextDouble()*2,lat=29+random.nextDouble()*2;
            check(Math.abs(EnvironmentRules.distance(lon,lat,120.2,30.2)-EnvironmentRules.distance(120.2,30.2,lon,lat))<1e-7,"distance symmetry "+i);
        }
        System.out.println("PASS: "+checks+" environment evidence/rule checks");
    }
}
