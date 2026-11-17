package com.ruoyi.skytwin;

import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.access.prepost.PreAuthorize;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.annotation.Log;
import com.ruoyi.common.enums.BusinessType;

@RestController
@RequestMapping("/sky/dispatch")
public class DispatchController extends BaseController {
    private final DispatchService service;
    public DispatchController(DispatchService service) { this.service=service; }
    @PostMapping("/plans") @PreAuthorize("@ss.hasPermi('sky:operate')") @Log(title="集群调度方案",businessType=BusinessType.INSERT)
    public AjaxResult preview(@Valid @RequestBody DispatchInputs.Preview input) { return success(service.preview(input,getUsername())); }
    @GetMapping("/plans") @PreAuthorize("@ss.hasPermi('sky:read')")
    public AjaxResult history() { return success(service.history()); }
    @GetMapping("/plans/{id}") @PreAuthorize("@ss.hasPermi('sky:read')")
    public AjaxResult detail(@PathVariable String id) { return success(service.detail(id)); }
    @PostMapping("/plans/{id}/confirm") @PreAuthorize("@ss.hasPermi('sky:operate')") @Log(title="集群批量派机",businessType=BusinessType.UPDATE)
    public AjaxResult confirm(@PathVariable String id,@Valid @RequestBody DispatchInputs.Confirm input) { return success(service.confirm(id,input,getUsername())); }
}
