// 物流配送
package com.ruoyi.skytwin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Max;
// 重量的精度规则
import jakarta.validation.constraints.Digits;

public final class LogisticsInputs{
// 请求DTO
    public record Create(
        // 货物名称
        //校验规则
        @NotBlank(message = "货物名称不能为空")
        @Size(max = 80, message = "货物名称最多80个字符")
        String cargoName,
        // 重量
        @NotNull(message = "重量不能为空")
        @DecimalMin(value = "0.01", message = "重量至少为0.01千克")
        @DecimalMax(value = "10000", message = "重量不能超过10000千克")
        @Digits(integer = 5, fraction = 2, message = "重量最多保留两位小数")
        Double weight,
    // 起点站
    @NotBlank(message = "请选择起点站")
    @Size(max = 40, message = "起点站编号最多40个字符")
    String startStationId,

    // 终点站
    @NotBlank(message = "请选择终点站")
    @Size(max = 40, message = "终点站编号最多40个字符")
    String endStationId,

    // 配送时限：分钟
    @NotNull(message = "请填写配送时限")
    @Min(value = 1, message = "配送时限至少1分钟")
    @Max(value = 1440, message = "配送时限最多1440分钟")
    Integer deadlineMinutes,

    // 创建原因
    @NotBlank(message = "请填写创建原因")
    @Size(max = 500, message = "创建原因最多500个字符")
    String reason
    ){}
    // 确认送达只需要填写原因。
    // 订单状态、确认人、确认时间都由服务端决定。
    public record Deliver(
        @NotBlank(message = "请填写确认送达原因")
        @Size(max = 500, message = "确认原因最多500个字符")
        String reason
    ) {}
}
