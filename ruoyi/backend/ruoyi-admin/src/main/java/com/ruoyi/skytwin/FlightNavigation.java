package com.ruoyi.skytwin;

/** Read-only projection of the same frozen route and simulation time used by SkyService. */
public final class FlightNavigation {
    private FlightNavigation() {}
    public record State(AirspaceEngine.Point position, double remainingRouteMeters,
        double destinationDistanceMeters, double remainingSimulationSeconds) {}
    public static State at(RouteEngine.Plan route, double elapsedSeconds, String status) {
        double elapsed = "completed".equals(status) ? route.durationSeconds()
            : Math.max(0, Math.min(route.durationSeconds(), elapsedSeconds));
        var position = RouteEngine.at(route.points(), elapsed);
        var end = route.points().get(route.points().size() - 1);
        double remaining = 0;
        var previous = position;
        for (var point : route.points()) {
            if (point.offsetSeconds() <= elapsed) continue;
            remaining += distance(previous, point);
            previous = point;
        }
        // Horizontal WGS84 distances: climbing/descending is not extra ground-route mileage.
        return new State(position, remaining, distance(position, end), route.durationSeconds() - elapsed);
    }
    private static double distance(AirspaceEngine.Point a, AirspaceEngine.Point b) {
        return RouteEngine.distance(new RouteEngine.Waypoint(a.longitude(), a.latitude()),
            new RouteEngine.Waypoint(b.longitude(), b.latitude()));
    }
}
