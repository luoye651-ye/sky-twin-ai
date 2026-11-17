package com.ruoyi.skytwin;
import java.util.List;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
public final class TrafficInputs {
    private TrafficInputs() {}
    public record Selection(@NotBlank @Size(max=40) String taskId,@Min(0) int expectedRevision) {}
    public record Preview(@NotNull @Size(min=1,max=20) List<@NotNull @Valid Selection> tasks,
        @Min(5) @Max(300) int leadSeconds,@Min(0) @Max(600) int maxDelaySeconds) {}
    public record Confirm(@NotBlank @Size(max=500) String reason) {}
}
