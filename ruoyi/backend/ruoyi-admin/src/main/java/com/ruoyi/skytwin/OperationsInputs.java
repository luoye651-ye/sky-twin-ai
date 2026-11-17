package com.ruoyi.skytwin;
import jakarta.validation.constraints.*;
import java.time.LocalDateTime;
public final class OperationsInputs {
    public record Retry(@NotBlank String requestId,@NotBlank @Size(max=500) String reason,@Min(1) @Max(1440) int deadlineMinutes){}
    public record Resource(@NotBlank String requestId,@NotBlank @Size(max=40) String aircraftId,@NotBlank @Pattern(regexp="charging|maintenance|fault") String kind,@NotBlank @Size(max=500) String reason){}
    public record Close(@NotBlank @Size(max=500) String reason,@NotNull @DecimalMin("0") @DecimalMax("100") Double battery){}
    public record Capacity(@Min(1) @Max(200) int capacity,@NotBlank @Size(max=500) String reason){}
    public record Flight(@NotBlank String requestId,@NotBlank @Size(max=80) String title,@NotBlank @Size(max=40) String startStationId,@NotBlank @Size(max=40) String endStationId,@NotNull LocalDateTime departureAt,@Min(1) @Max(20) int seats,@NotBlank @Size(max=500) String reason){}
    public record Booking(@NotBlank String requestId,@Min(1) @Max(20) int seats){}
    public record FlightAction(@Min(1) int expectedRevision,LocalDateTime departureAt,@NotBlank @Size(max=500) String reason){}
    public record Report(@NotBlank String requestId,@NotBlank @Pattern(regexp="task|discovery") String sourceKind,@NotBlank @Size(max=40) String sourceId){}
    public record ReportEdit(@Min(1) int expectedRevision,@NotBlank @Size(max=20000) String content,@NotBlank @Pattern(regexp="manual|ai_assisted") String source,boolean publish){}
}
