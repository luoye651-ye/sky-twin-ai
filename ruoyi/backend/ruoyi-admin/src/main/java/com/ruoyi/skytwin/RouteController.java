package com.ruoyi.skytwin;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.access.prepost.PreAuthorize;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
@RestController
@RequestMapping("/sky/tasks/{taskId}/route")
public class RouteController extends BaseController {
    private final RouteService service;
    public RouteController(RouteService service) { this.service=service; }
    @GetMapping @PreAuthorize("@ss.hasPermi('sky:read')")
    public AjaxResult detail(@PathVariable String taskId) { return success(service.detail(taskId)); }
    @GetMapping("/versions/{revision}") @PreAuthorize("@ss.hasPermi('sky:read')")
    public AjaxResult version(@PathVariable String taskId,@PathVariable int revision) { return success(service.version(taskId,revision)); }
    @PostMapping("/preview") @PreAuthorize("@ss.hasPermi('sky:operate')")
    public AjaxResult preview(@PathVariable String taskId,@Valid @RequestBody RouteInputs.Save input) { return success(service.preview(taskId,input,getUsername())); }
    @PostMapping("/suggest") @PreAuthorize("@ss.hasPermi('sky:operate')")
    public AjaxResult suggest(@PathVariable String taskId,@Valid @RequestBody RouteInputs.Save input) { return success(service.suggest(taskId,input,getUsername())); }
    @PutMapping @PreAuthorize("@ss.hasPermi('sky:operate')")
    public AjaxResult save(@PathVariable String taskId,@Valid @RequestBody RouteInputs.Save input) { return success(service.save(taskId,input,getUsername())); }
}
