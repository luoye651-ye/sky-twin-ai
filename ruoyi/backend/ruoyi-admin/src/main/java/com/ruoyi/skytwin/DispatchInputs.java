package com.ruoyi.skytwin;

import java.util.List;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;

public final class DispatchInputs {
    private DispatchInputs() {}
    public record Selection(@NotBlank @Size(max=40) String taskId, @NotNull @Min(1) @Max(3) Integer priority) {}
    public record Preview(@NotEmpty @Size(max=20) List<@NotNull @Valid Selection> tasks,
        @Size(max=200) List<@NotBlank @Size(max=40) String> aircraftIds) {}
    public record Confirm(@NotBlank @Size(max=500) String reason) {}
}
