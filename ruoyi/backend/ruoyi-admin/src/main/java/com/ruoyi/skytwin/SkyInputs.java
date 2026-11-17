package com.ruoyi.skytwin;

import jakarta.validation.constraints.*;

/** Input records keep configuration separate from server-owned runtime states. */
public final class SkyInputs {
    private SkyInputs() {}
    public record Aircraft(
        @NotBlank @Size(max=80) String name,
        @NotBlank @Pattern(regexp="drone|cargo|evtol") String type,
        @NotBlank @Size(max=80) String model,
        @NotNull @DecimalMin("-180") @DecimalMax("180") Double longitude,
        @NotNull @DecimalMin("-90") @DecimalMax("90") Double latitude,
        @NotNull @DecimalMin("0") @DecimalMax("100") Double battery,
        @NotNull @DecimalMin("0") @DecimalMax("10000") Double payloadCapacity,
        @NotNull @Min(0) @Max(20) Integer seats) {}
    public record Station(
        @NotBlank @Size(max=80) String name,
        @NotBlank @Pattern(regexp="takeoff|logistics|charging|emergency|vertiport") String type,
        @NotNull @DecimalMin("-180") @DecimalMax("180") Double longitude,
        @NotNull @DecimalMin("-90") @DecimalMax("90") Double latitude,
        @NotBlank @Pattern(regexp="enabled|disabled") String status) {}
    public record Task(
        @NotBlank @Size(max=100) String title,
        @NotBlank @Pattern(regexp="logistics|commute|environment|rescue|airspace") String type,
        @NotBlank @Size(max=40) String startStationId,
        @NotBlank @Size(max=40) String endStationId,
        @NotNull @DecimalMin("0") @DecimalMax("10000") Double payload,
        @NotNull @Min(0) @Max(20) Integer passengers,
        @NotNull @DecimalMin("1") @DecimalMax("50") Double speed,
        @NotNull @DecimalMin("20") @DecimalMax("120") Double cruiseAltitude,
        @NotBlank @Size(max=500) String reason) {}
    public record Action(@Size(max=40) String aircraftId, @NotBlank @Size(max=500) String reason) {}
}
