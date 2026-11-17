package com.ruoyi.skytwin;
import java.io.*;
import java.security.MessageDigest;
import java.util.HexFormat;
import javax.imageio.ImageIO;
import javax.imageio.stream.MemoryCacheImageInputStream;
/** Bounded PNG/JPEG decoding; original bytes retained in the same DB transaction as evidence. */
public record EnvironmentImage(byte[] bytes,String mime,String sha256,int width,int height,String originalName) {
    public static String hash(byte[] bytes) {
        try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes)); }
        catch(Exception e) { throw new IllegalStateException(e); }
    }
    public static EnvironmentImage read(byte[] bytes,String name) {
        if(bytes.length==0 || bytes.length>2*1024*1024) throw new IllegalArgumentException("图片应为1字节至2MiB的PNG或JPEG");
        try(var stream=new MemoryCacheImageInputStream(new ByteArrayInputStream(bytes))) {
            var readers=ImageIO.getImageReaders(stream);
            if(!readers.hasNext()) throw new IllegalArgumentException("无法解码图片，必须上传PNG或JPEG");
            var reader=readers.next();
            try {
                String format=reader.getFormatName().toLowerCase(java.util.Locale.ROOT);
                if(!format.equals("png") && !format.equals("jpeg") && !format.equals("jpg")) throw new IllegalArgumentException("只允许PNG或JPEG，不接受SVG/GIF/脚本");
                reader.setInput(stream,true,true);int w=reader.getWidth(0),h=reader.getHeight(0);
                if(w<1 || h<1 || w>4096 || h>4096 || (long)w*h>12000000) throw new IllegalArgumentException("图片尺寸最多4096×4096且不超过1200万像素");
                if(reader.read(0)==null) throw new IllegalArgumentException("图片解码失败");
                String safe=name==null?"image":name.replace('\\','/');safe=safe.substring(safe.lastIndexOf('/')+1).replaceAll("[\\p{Cntrl}]","");
                if(safe.length()>100) safe=safe.substring(0,100);
                return new EnvironmentImage(bytes,format.equals("png")?"image/png":"image/jpeg",hash(bytes),w,h,safe);
            } finally { reader.dispose(); }
        } catch(IOException e) { throw new IllegalArgumentException("图片内容不完整或无法解码",e); }
    }
}
