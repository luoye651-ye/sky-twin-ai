package com.ruoyi.skytwin;

import java.io.IOException;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Component;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

/** Short-lived streams reauthenticate through the JWT filter on reconnection. */
@Component
public class SkyStreams {
    private final SkyService service;
    private final ConcurrentHashMap<SseEmitter,Boolean> clients=new ConcurrentHashMap<>();
    public SkyStreams(SkyService service) { this.service=service; }
    public SseEmitter connect() {
        var emitter=new SseEmitter(20000L);
        emitter.onCompletion(()->clients.remove(emitter));
        emitter.onTimeout(()->{ clients.remove(emitter); emitter.complete(); });
        emitter.onError(error->clients.remove(emitter));
        clients.put(emitter,true);
        try { emitter.send(SseEmitter.event().name("snapshot").data(service.snapshot())); }
        catch(IOException e) { clients.remove(emitter); emitter.completeWithError(e); }
        return emitter;
    }
    @Scheduled(fixedDelay=2000,initialDelay=10000)
    public void broadcast() {
        if(clients.isEmpty()) return;
        var snapshot=service.snapshot();
        for(var emitter:clients.keySet()) {
            try { emitter.send(SseEmitter.event().name("snapshot").data(snapshot)); }
            catch(Exception e) { clients.remove(emitter); emitter.complete(); }
        }
    }
}
