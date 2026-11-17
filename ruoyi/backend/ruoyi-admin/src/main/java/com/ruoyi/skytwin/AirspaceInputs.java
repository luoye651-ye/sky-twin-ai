package com.ruoyi.skytwin;

import java.time.LocalDateTime;
import jakarta.validation.constraints.*;

public final class AirspaceInputs {
    private AirspaceInputs() {}
    public record Zone(@NotBlank @Size(max=80) String name,
        @NotBlank @Pattern(regexp="no_fly|height_limit") String type,
        @NotNull @DecimalMin("-180") @DecimalMax("180") Double west,
        @NotNull @DecimalMin("-90") @DecimalMax("90") Double south,
        @NotNull @DecimalMin("-180") @DecimalMax("180") Double east,
        @NotNull @DecimalMin("-90") @DecimalMax("90") Double north,
        @NotNull @DecimalMin("0") @DecimalMax("1000") Double minAltitude,
        @NotNull @DecimalMin("0") @DecimalMax("1000") Double maxAltitude,
        LocalDateTime startsAt,LocalDateTime endsAt,@NotNull Boolean enabled,
        @NotBlank @Size(max=500) String reason) {}
    public record Validate(@NotBlank @Size(max=40) String taskId,LocalDateTime departureAt) {}
}
