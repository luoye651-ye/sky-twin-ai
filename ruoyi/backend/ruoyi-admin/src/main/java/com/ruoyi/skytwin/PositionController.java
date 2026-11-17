package com.ruoyi.skytwin;

import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.access.prepost.PreAuthorize;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.exception.ServiceException;
import java.util.Map;

@RestController
@RequestMapping("/sky/positioning")
public class PositionController extends BaseController {
    private final PositionService service;
    public PositionController(PositionService service) { this.service=service; }
    @GetMapping("/devices") @PreAuthorize("@ss.hasPermi('sky:read')")
    public AjaxResult devices() { return success(service.devices()); }
    @PostMapping("/devices") @PreAuthorize("@ss.hasPermi('sky:manage')")
    public AjaxResult create(@Valid @RequestBody PositionInputs.Device input) { return success((Object)service.create(input,getUsername())); }
    @PostMapping("/devices/{id}/mode") @PreAuthorize("@ss.hasPermi('sky:operate')")
    public AjaxResult mode(@PathVariable String id,@Valid @RequestBody PositionInputs.Mode input) { return success(service.mode(id,input,getUsername())); }
    @PostMapping("/devices/{id}/samples") @PreAuthorize("@ss.hasPermi('sky:operate')")
    public AjaxResult ingest(@PathVariable String id,@Valid @RequestBody PositionInputs.Sample input) { return success(service.ingest(id,input)); }
    @PostMapping("/devices/{id}/nmea-samples") @PreAuthorize("@ss.hasPermi('sky:operate')")
    public AjaxResult ingestNmea(@PathVariable String id,@Valid @RequestBody PositionInputs.NmeaSample input) {
        final NmeaGga.Fix fix;
        try { fix=NmeaGga.decode(input.gga(),input.utcDate(),input.takeoffAltitudeMsl()); }
        catch(RuntimeException e) { throw new ServiceException("NMEA解析失败："+e.getMessage(),400); }
        // Invoke the same proxied transactional service as JSON samples. Never trust a client source flag.
        var receipt=service.ingest(id,new PositionInputs.Sample(input.sessionId(),input.sequence(),fix.sampledAt(),
            fix.longitude(),fix.latitude(),fix.relativeAltitude(),fix.fixValid()));
        return success(Map.of("receipt",receipt,"decoded",fix,"simulation",true,"source","simulated_terminal"));
    }
    @GetMapping("/devices/{id}/samples") @PreAuthorize("@ss.hasPermi('sky:read')")
    public AjaxResult samples(@PathVariable String id,@RequestParam String from,@RequestParam String to,
        @RequestParam(defaultValue="0") long after,@RequestParam(defaultValue="1000") int limit,@RequestParam(defaultValue="true") boolean acceptedOnly) {
        return success(service.samples(id,from,to,after,limit,acceptedOnly));
    }
    @GetMapping("/devices/{id}/recent") @PreAuthorize("@ss.hasPermi('sky:read')")
    public AjaxResult recent(@PathVariable String id) { return success(service.recent(id)); }
}
