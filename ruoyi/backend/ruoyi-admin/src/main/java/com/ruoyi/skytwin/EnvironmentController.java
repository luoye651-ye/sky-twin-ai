package com.ruoyi.skytwin;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.http.*;
import com.ruoyi.common.exception.ServiceException;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
@RestController @RequestMapping("/sky/environment")
public class EnvironmentController extends BaseController {
    private final EnvironmentService service; private final VisionAnalysisService vision;
    public EnvironmentController(EnvironmentService service,VisionAnalysisService vision) { this.service=service;this.vision=vision; }
    private EnvironmentImage image(MultipartFile file) {
        try {
            if(file.getSize()>2*1024*1024) throw new IllegalArgumentException("图片最多2MiB");
            return EnvironmentImage.read(file.getBytes(),file.getOriginalFilename());
        } catch(java.io.IOException|IllegalArgumentException e) { throw new ServiceException(e.getMessage(),400); }
    }
    @PostMapping(value="/analyses",consumes=MediaType.MULTIPART_FORM_DATA_VALUE) @PreAuthorize("@ss.hasPermi('sky:operate')")
    public AjaxResult analyze(@RequestParam String requestId,@RequestPart("image") MultipartFile file) { return success(vision.analyze(requestId,image(file),getUsername())); }
    @GetMapping("/analyses/{id}") @PreAuthorize("@ss.hasPermi('sky:read')")
    public AjaxResult analysis(@PathVariable String id) { return success(vision.detail(id)); }
    @GetMapping("/analyses/{id}/image") @PreAuthorize("@ss.hasPermi('sky:read')")
    public ResponseEntity<byte[]> analysisImage(@PathVariable String id) {
        var row=vision.image(id);
        return ResponseEntity.ok().contentType(MediaType.parseMediaType(row.get("imageMime").toString())).cacheControl(CacheControl.noStore())
            .header("X-Content-Type-Options","nosniff").header("Content-Disposition","inline; filename=\"analysis-evidence\"").body((byte[])row.get("imageBytes"));
    }
    @GetMapping("/discoveries") @PreAuthorize("@ss.hasPermi('sky:read')") public AjaxResult list(@RequestParam(required=false) String status) { return success(service.list(status)); }
    @GetMapping("/discoveries/{id}") @PreAuthorize("@ss.hasPermi('sky:read')") public AjaxResult detail(@PathVariable String id) { return success(service.detail(id)); }
    @PostMapping(value="/discoveries",consumes=MediaType.MULTIPART_FORM_DATA_VALUE) @PreAuthorize("@ss.hasPermi('sky:operate')")
    public AjaxResult create(@Valid @RequestPart("input") EnvironmentInputs.Discovery input,@RequestPart("image") MultipartFile file) { return success(service.create(input,image(file),getUsername())); }
    @PostMapping("/discoveries/{id}/review") @PreAuthorize("@ss.hasPermi('sky:operate')") public AjaxResult review(@PathVariable String id,@Valid @RequestBody EnvironmentInputs.Review input) { return success(service.review(id,input,getUsername())); }
    @PostMapping("/discoveries/{id}/responses") @PreAuthorize("@ss.hasPermi('sky:operate')") public AjaxResult respond(@PathVariable String id,@Valid @RequestBody EnvironmentInputs.Response input) { return success(service.respond(id,input,getUsername())); }
    @PostMapping(value="/discoveries/{id}/close",consumes=MediaType.MULTIPART_FORM_DATA_VALUE) @PreAuthorize("@ss.hasPermi('sky:operate')")
    public AjaxResult close(@PathVariable String id,@Valid @RequestPart("input") EnvironmentInputs.Close input,@RequestPart("image") MultipartFile file) { return success(service.close(id,input,image(file),getUsername())); }
    @GetMapping("/discoveries/{id}/image") @PreAuthorize("@ss.hasPermi('sky:read')") public ResponseEntity<byte[]> image(@PathVariable String id,@RequestParam(defaultValue="false") boolean after) {
        var row=service.image(id,after);
        return ResponseEntity.ok().contentType(MediaType.parseMediaType(row.get("imageMime").toString())).cacheControl(CacheControl.noStore())
            .header("X-Content-Type-Options","nosniff").header("Content-Disposition","inline; filename=\"evidence\"").body((byte[])row.get("imageBytes"));
    }
    @GetMapping("/reports") @PreAuthorize("@ss.hasPermi('sky:read')") public AjaxResult reports() { return success(service.reports()); }
    @GetMapping("/reports/{id}") @PreAuthorize("@ss.hasPermi('sky:read')") public AjaxResult report(@PathVariable String id) { return success(service.report(id)); }
}
