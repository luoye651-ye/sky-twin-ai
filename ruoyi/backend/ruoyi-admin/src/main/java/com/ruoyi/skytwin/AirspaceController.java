package com.ruoyi.skytwin;

import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.access.prepost.PreAuthorize;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.annotation.Log;
import com.ruoyi.common.enums.BusinessType;

@RestController
@RequestMapping("/sky/airspace")
public class AirspaceController extends BaseController {
    private final AirspaceService service;
    public AirspaceController(AirspaceService service) { this.service=service; }
    @GetMapping("/zones") @PreAuthorize("@ss.hasPermi('sky:read')")
    public AjaxResult zones() { return success(service.zones()); }
    @PostMapping("/zones") @PreAuthorize("@ss.hasPermi('sky:manage')") @Log(title="空域区域",businessType=BusinessType.INSERT)
    public AjaxResult create(@Valid @RequestBody AirspaceInputs.Zone input) { return success((Object)service.save(null,input,getUsername())); }
    @PutMapping("/zones/{id}") @PreAuthorize("@ss.hasPermi('sky:manage')") @Log(title="空域区域",businessType=BusinessType.UPDATE)
    public AjaxResult update(@PathVariable String id,@Valid @RequestBody AirspaceInputs.Zone input) { return success((Object)service.save(id,input,getUsername())); }
    @PostMapping("/validate") @PreAuthorize("@ss.hasPermi('sky:operate')")
    public AjaxResult validate(@Valid @RequestBody AirspaceInputs.Validate input) { return success(service.validate(input,getUsername())); }
    @GetMapping("/checks") @PreAuthorize("@ss.hasPermi('sky:read')")
    public AjaxResult checks() { return success(service.checks()); }
    @GetMapping("/checks/{id}") @PreAuthorize("@ss.hasPermi('sky:read')")
    public AjaxResult detail(@PathVariable String id) { return success(service.checkDetail(id)); }
}
