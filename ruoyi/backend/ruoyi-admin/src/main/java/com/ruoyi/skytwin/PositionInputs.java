package com.ruoyi.skytwin;

import jakarta.validation.constraints.*;

public final class PositionInputs {
    private PositionInputs() {}
    public record Device(@NotBlank @Pattern(regexp="[A-Za-z0-9_-]{1,64}") String id,
        @NotBlank @Size(max=80) String name, @NotBlank @Size(max=64) String aircraftId) {}
    public record Mode(@NotNull Boolean enabled, @NotBlank @Size(max=500) String reason) {}
    public record NmeaSample(@NotBlank @Size(max=64) String sessionId,
        @NotNull @Min(0) @Max(9007199254740991L) Long sequence,
        @NotBlank @Size(max=160) String gga, @NotBlank @Size(max=10) String utcDate,
        @NotNull @DecimalMin("-1000") @DecimalMax("10000") Double takeoffAltitudeMsl) {}
    public record Sample(@NotBlank @Size(max=64) String sessionId,
        @NotNull @Min(0) @Max(9007199254740991L) Long sequence,
        @NotBlank @Size(max=40) String sampledAt,
        @NotNull @DecimalMin("-180") @DecimalMax("180") Double longitude,
        @NotNull @DecimalMin("-90") @DecimalMax("90") Double latitude,
        @NotNull @DecimalMin("-100") @DecimalMax("10000") Double altitude,
        @NotNull Boolean fixValid) {}
}
