package com.ruoyi.skytwin;
import java.util.*;

public class FlightNavigationChecks {
    private static int checks;
    private static void check(boolean ok) { checks++; if (!ok) throw new AssertionError("Navigation check " + checks); }
    private static void near(double a, double b) { check(Math.abs(a - b) < 1e-6); }
    public static void main(String[] args) {
        var from = new RouteEngine.Waypoint(120.19, 30.215);
        var to = new RouteEngine.Waypoint(120.193, 30.215);
        var plan = RouteEngine.build(2, from, to, List.of(new RouteEngine.Waypoint(120.19, 30.225),
            new RouteEngine.Waypoint(120.193, 30.225)), 10, 60, null);
        var start = FlightNavigation.at(plan, 0, "assigned");
        near(start.remainingRouteMeters(), plan.distanceMeters());
        check(start.remainingRouteMeters() > start.destinationDistanceMeters() * 5);
        near(start.position().altitude(), 0);
        var climb = FlightNavigation.at(plan, plan.durationSeconds() * .05, "executing");
        near(climb.remainingRouteMeters(), start.remainingRouteMeters());
        near(climb.position().altitude(), 30);
        double previous = start.remainingRouteMeters();
        for (int i = 0; i <= plan.durationSeconds(); i++) {
            var live = FlightNavigation.at(plan, i, "executing");
            check(live.remainingRouteMeters() <= previous + 1e-6);
            check(live.remainingRouteMeters() + 1e-6 >= live.destinationDistanceMeters());
            check(live.remainingSimulationSeconds() >= 0);
            check(live.position().equals(RouteEngine.at(plan.points(), i)));
            previous = live.remainingRouteMeters();
        }
        var descent = FlightNavigation.at(plan, plan.durationSeconds() * .95, "executing");
        near(descent.remainingRouteMeters(), 0); near(descent.destinationDistanceMeters(), 0);
        check(descent.remainingSimulationSeconds() > 0 && descent.position().altitude() > 0);
        var completed = FlightNavigation.at(plan, 1, "completed");
        near(completed.remainingRouteMeters(), 0); near(completed.remainingSimulationSeconds(), 0); near(completed.position().altitude(), 0);
        check(completed.position().longitude() == to.longitude());
        var stopped = FlightNavigation.at(plan, 5, "cancelled");
        check(stopped.equals(FlightNavigation.at(plan, 5, "failed")));
        check(stopped.remainingRouteMeters() > 0);
        near(FlightNavigation.at(plan, -5, "created").remainingRouteMeters(), start.remainingRouteMeters());
        near(FlightNavigation.at(plan, 99999, "executing").remainingRouteMeters(), 0);
        var legacy = RouteEngine.legacy(from, to, 10, 60, 20);
        near(FlightNavigation.at(legacy, 0, "assigned").remainingRouteMeters(), legacy.distanceMeters());
        System.out.println("PASS: " + checks + " server navigation distance/position/state checks");
    }
}
