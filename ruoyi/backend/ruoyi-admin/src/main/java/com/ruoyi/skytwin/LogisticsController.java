package com.ruoyi.skytwin;

import jakarta.validation.Valid;

import org.springframework.web.bind.annotation.*;
import org.springframework.security.access.prepost.PreAuthorize;

import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.annotation.Log;
import com.ruoyi.common.enums.BusinessType;

// 标记为HTTP请求入口，返回的数据会转换成JSON。
@RestController
@RequestMapping("/sky/logistics/orders")
public class LogisticsController extends BaseController{
    private final LogisticsService service;
    // Spring 传入刚才编写的订单业务服务。
    public LogisticsController(LogisticsService service){
        this.service = service;
    }
    // 接收POST /sky/logistics/orders请求。
    @PostMapping
    // 必须具有订单操作所复用的sky：operate权限。
    @PreAuthorize("@ss.hasPermi('sky:operate')")
    // 使用若依的操作日志功能。
    @Log(title = "配送订单", businessType = BusinessType.INSERT)
    public AjaxResult create(
        @Valid @RequestBody LogisticsInputs.Create x)
    {
        /*
        * RequestBody：把请求中的 JSON 转成 Create 对象。
        * Valid：触发你之前写的 NotBlank、Min 等校验。
        * getUsername()：从登录身份获取创建人，不相信前端自报姓名。
        */
       String orderId = service.create(x,getUsername());
        /*
        * 返回成功响应，把订单编号放入 data。
        * 若依的 success(String) 会将字符串当作消息，
        * 因此这里转换为 Object。
        */
       return success((Object) orderId);
    }
    // 查询配送订单列表
    @GetMapping
    @PreAuthorize("@ss.hasPermi('sky:read')")
    public AjaxResult list(){
        return success(service.list());
    }

    @GetMapping("/{id}")
    @PreAuthorize("@ss.hasPermi('sky:read')")
    public AjaxResult detail(@PathVariable("id") String id) {
        return success(service.detail(id));
    }

    @GetMapping("/{id}/tracks")
    @PreAuthorize("@ss.hasPermi('sky:read')")
    public AjaxResult tracks(@PathVariable("id") String id) {
        return success(service.tracks(id));
    }

    @PostMapping("/{id}/{action:assign|start|cancel}")
    @PreAuthorize("@ss.hasPermi('sky:operate')")
    @Log(title = "配送调度", businessType = BusinessType.UPDATE)
    public AjaxResult action(@PathVariable("id") String id,
                            @PathVariable("action") String action,
                            @Valid @RequestBody SkyInputs.Action x) {
        service.action(id, action, x, getUsername());
        return success();
    }
    @PostMapping("/{id}/deliver")
    @PreAuthorize("@ss.hasPermi('sky:operate')")
    @Log(title = "确认送达", businessType = BusinessType.UPDATE)
    public AjaxResult deliver(
        @PathVariable("id") String id,
        @Valid @RequestBody LogisticsInputs.Deliver x
    ) {
        // 确认人从登录身份获取，不允许前端冒用。
        service.deliver(id, x, getUsername());
        return success();
    }
}
