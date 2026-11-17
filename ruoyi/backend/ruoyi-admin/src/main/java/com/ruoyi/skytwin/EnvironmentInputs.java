package com.ruoyi.skytwin;
import java.time.Instant;
import java.util.List;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
public final class EnvironmentInputs {
    private EnvironmentInputs() {}
    public record Box(@NotNull @DecimalMin("0") @DecimalMax("1") Double x,
        @NotNull @DecimalMin("0") @DecimalMax("1") Double y,
        @NotNull @DecimalMin(value="0",inclusive=false) @DecimalMax("1") Double width,
        @NotNull @DecimalMin(value="0",inclusive=false) @DecimalMax("1") Double height,
        @NotNull @Size(max=200) String note) {}
    public record Discovery(@NotBlank @Pattern(regexp="[a-fA-F0-9-]{36}") String requestId,
        @NotBlank @Size(max=40) String taskId,@NotBlank @Size(max=80) String title,
        @NotNull @DecimalMin("-180") @DecimalMax("180") Double longitude,
        @NotNull @DecimalMin("-90") @DecimalMax("90") Double latitude,
        @NotNull Instant observedAt,@NotBlank @Pattern(regexp="simulation|user_upload") String imageSource,
        @NotNull @Size(min=1,max=20) List<@NotNull @Valid Box> annotations,
        @Pattern(regexp="[a-f0-9-]{36}") String analysisId) {}
    public record Review(@NotBlank @Pattern(regexp="confirm|reject") String decision,
        @NotBlank @Pattern(regexp="low|medium|high") String severity,@NotBlank @Size(max=500) String reason) {}
    public record Response(@NotBlank @Size(max=40) String startStationId,@NotBlank @Size(max=40) String endStationId,
        @NotBlank @Size(max=500) String reason) {}
    public record Close(@NotBlank @Size(max=500) String resolution) {}
}
