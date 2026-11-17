package com.ruoyi.skytwin;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Bean;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.scheduling.concurrent.ThreadPoolTaskScheduler;

@Configuration
@EnableScheduling
public class SkySimulation {
    private static final Logger log=LoggerFactory.getLogger(SkySimulation.class);
    private final SkyService service;
    public SkySimulation(SkyService service) { this.service=service; }
    @Bean
    public ThreadPoolTaskScheduler skyTaskScheduler() {
        var scheduler=new ThreadPoolTaskScheduler(); scheduler.setPoolSize(4); scheduler.setThreadNamePrefix("sky-sim-"); return scheduler;
    }
    @Scheduled(fixedDelay=1000,initialDelay=10000)
    public void tick() {
        try { service.advanceSimulation(); }
        catch(Exception e) { log.error("Simulation cycle failed; clock and ALL aircraft rolled back together",e); }
    }
}
