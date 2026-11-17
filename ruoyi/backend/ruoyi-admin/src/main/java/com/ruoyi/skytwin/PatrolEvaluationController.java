package com.ruoyi.skytwin;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.http.*;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;

@RestController @RequestMapping("/sky/patrol-evaluation")
public class PatrolEvaluationController extends BaseController {
    private final PatrolEvaluationService service;
    public PatrolEvaluationController(PatrolEvaluationService service){this.service=service;}
    public record Start(@NotBlank @Pattern(regexp="[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}") String requestId){}
    @GetMapping("/config") @PreAuthorize("@ss.hasPermi('sky:read')") public AjaxResult config(){return success(service.config());}
    @GetMapping("/runs") @PreAuthorize("@ss.hasPermi('sky:read')") public AjaxResult list(){return success(service.list());}
    @GetMapping("/runs/{id}") @PreAuthorize("@ss.hasPermi('sky:read')") public AjaxResult detail(@PathVariable String id){return success(service.detail(id));}
    @PostMapping("/runs") @PreAuthorize("@ss.hasPermi('sky:operate')") public AjaxResult start(@Valid @RequestBody Start input){return success(service.start(input.requestId(),getUsername()));}
    @GetMapping("/runs/{id}/images/{imageId}") @PreAuthorize("@ss.hasPermi('sky:read')")
    public ResponseEntity<byte[]> image(@PathVariable String id,@PathVariable String imageId,@RequestParam(defaultValue="predicted") String kind){
        return ResponseEntity.ok().contentType(MediaType.IMAGE_JPEG).cacheControl(CacheControl.noStore()).header("X-Content-Type-Options","nosniff")
            .body(service.image(id,imageId,kind));
    }
}
