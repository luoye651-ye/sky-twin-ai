package com.ruoyi.skytwin;
import java.util.List;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
public final class RouteInputs {
    private RouteInputs() {}
    public record Waypoint(@NotNull @DecimalMin("-180") @DecimalMax("180") Double longitude,
        @NotNull @DecimalMin("-90") @DecimalMax("90") Double latitude) {}
    public record Save(@NotNull @Min(0) Integer expectedRevision,@NotNull @Size(max=24) List<@NotNull @Valid Waypoint> waypoints,
        @NotBlank @Size(max=500) String reason) {}
}
