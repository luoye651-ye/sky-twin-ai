package com.ruoyi.skytwin;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.access.prepost.PreAuthorize;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
@RestController @RequestMapping("/sky/traffic")
public class TrafficController extends BaseController {
    private final TrafficService service;
    public TrafficController(TrafficService service) { this.service=service; }
    @GetMapping @PreAuthorize("@ss.hasPermi('sky:read')") public AjaxResult state() { return success(service.state()); }
    @GetMapping("/plans/{id}") @PreAuthorize("@ss.hasPermi('sky:read')") public AjaxResult detail(@PathVariable String id) { return success(service.detail(id)); }
    @GetMapping("/checks/{id}") @PreAuthorize("@ss.hasPermi('sky:read')") public AjaxResult evidence(@PathVariable String id) { return success(service.checkDetail(id)); }
    @PostMapping("/plans") @PreAuthorize("@ss.hasPermi('sky:operate')") public AjaxResult preview(@Valid @RequestBody TrafficInputs.Preview input) { return success(service.preview(input,getUsername())); }
    @PostMapping("/plans/{id}/confirm") @PreAuthorize("@ss.hasPermi('sky:operate')") public AjaxResult confirm(@PathVariable String id,@Valid @RequestBody TrafficInputs.Confirm input) { return success(service.confirm(id,input,getUsername())); }
    @PostMapping("/slots/{taskId}/cancel") @PreAuthorize("@ss.hasPermi('sky:operate')") public AjaxResult cancel(@PathVariable String taskId,@Valid @RequestBody TrafficInputs.Confirm input) { service.cancel(taskId,input,getUsername());return success(); }
}
