package com.ruoyi.skytwin;

import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.annotation.Log;
import com.ruoyi.common.enums.BusinessType;

@RestController
@RequestMapping("/sky")
public class SkyController extends BaseController {
    private final SkyService service;
    private final SkyStreams streams;
    public SkyController(SkyService service,SkyStreams streams) { this.service=service; this.streams=streams; }
    @GetMapping("/snapshot") @PreAuthorize("@ss.hasPermi('sky:read')")
    public AjaxResult snapshot() { return success(service.snapshot()); }
    @GetMapping(value="/stream",produces="text/event-stream") @PreAuthorize("@ss.hasPermi('sky:read')")
    public SseEmitter stream() { return streams.connect(); }
    @GetMapping("/aircraft") @PreAuthorize("@ss.hasPermi('sky:read')")
    public AjaxResult aircraft() { return success(service.aircraft()); }
    @PostMapping("/aircraft") @PreAuthorize("@ss.hasPermi('sky:manage')") @Log(title="飞行器",businessType=BusinessType.INSERT)
    public AjaxResult addAircraft(@Valid @RequestBody SkyInputs.Aircraft x) { return success((Object)service.saveAircraft(null,x,getUsername())); }
    @PutMapping("/aircraft/{id}") @PreAuthorize("@ss.hasPermi('sky:manage')") @Log(title="飞行器",businessType=BusinessType.UPDATE)
    public AjaxResult editAircraft(@PathVariable String id,@Valid @RequestBody SkyInputs.Aircraft x) { return success((Object)service.saveAircraft(id,x,getUsername())); }
    @DeleteMapping("/aircraft/{id}") @PreAuthorize("@ss.hasPermi('sky:manage')") @Log(title="飞行器",businessType=BusinessType.DELETE)
    public AjaxResult removeAircraft(@PathVariable String id) { service.removeAircraft(id,getUsername()); return success(); }
    @GetMapping("/stations") @PreAuthorize("@ss.hasPermi('sky:read')")
    public AjaxResult stations() { return success(service.stations()); }
    @PostMapping("/stations") @PreAuthorize("@ss.hasPermi('sky:manage')") @Log(title="站点",businessType=BusinessType.INSERT)
    public AjaxResult addStation(@Valid @RequestBody SkyInputs.Station x) { return success((Object)service.saveStation(null,x,getUsername())); }
    @PutMapping("/stations/{id}") @PreAuthorize("@ss.hasPermi('sky:manage')") @Log(title="站点",businessType=BusinessType.UPDATE)
    public AjaxResult editStation(@PathVariable String id,@Valid @RequestBody SkyInputs.Station x) { return success((Object)service.saveStation(id,x,getUsername())); }
    @DeleteMapping("/stations/{id}") @PreAuthorize("@ss.hasPermi('sky:manage')") @Log(title="站点",businessType=BusinessType.DELETE)
    public AjaxResult removeStation(@PathVariable String id) { service.removeStation(id,getUsername()); return success(); }
    @GetMapping("/tasks") @PreAuthorize("@ss.hasPermi('sky:read')")
    public AjaxResult tasks() { return success(service.tasks()); }
    @PostMapping("/tasks") @PreAuthorize("@ss.hasPermi('sky:operate')") @Log(title="低空任务",businessType=BusinessType.INSERT)
    public AjaxResult createTask(@Valid @RequestBody SkyInputs.Task x) { return success((Object)service.createTask(x,getUsername())); }
    @PostMapping("/tasks/{id}/{action}") @PreAuthorize("@ss.hasPermi('sky:operate')") @Log(title="任务调度",businessType=BusinessType.UPDATE)
    public AjaxResult taskAction(@PathVariable String id,@PathVariable String action,@Valid @RequestBody SkyInputs.Action x) { service.taskAction(id,action,x,getUsername()); return success(); }
    @GetMapping("/tasks/{id}/tracks") @PreAuthorize("@ss.hasPermi('sky:read')")
    public AjaxResult tracks(@PathVariable String id) { return success(service.tracks(id)); }
    @GetMapping("/events") @PreAuthorize("@ss.hasPermi('sky:read')")
    public AjaxResult events() { return success(service.events()); }
    @PostMapping("/events/{id}/resolve") @PreAuthorize("@ss.hasPermi('sky:operate')") @Log(title="事件处置",businessType=BusinessType.UPDATE)
    public AjaxResult resolve(@PathVariable long id,@Valid @RequestBody SkyInputs.Action x) { service.resolveEvent(id,x.reason(),getUsername()); return success(); }
    @GetMapping("/reports") @PreAuthorize("@ss.hasPermi('sky:read')")
    public AjaxResult reports() { return success(service.reports()); }
    @GetMapping("/audit") @PreAuthorize("@ss.hasPermi('sky:read')")
    public AjaxResult audit() { return success(service.audits()); }
}
