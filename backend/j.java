// Define a structure to hold route information
// This would be pre-populated from the world model
Structure Route:
    String name
    Float safetyScore
    Array<Pair<Float time, Float probability>> timeOutcomes

// Main function for the agent's decision-making
FUNCTION SelectAndMonitorRoute(Array<Route> allAvailableRoutes, Float delayThreshold = 2.0):

    // --- Step 1 & 2: Compute expected utilities and select best route ---
    Route bestRoute = NULL
    Float maxUtility = -INFINITY

    FOR EACH route IN allAvailableRoutes:
        // Calculate expected travel time
        Float expectedTime = 0.0
        FOR EACH outcome IN route.timeOutcomes:
            expectedTime = expectedTime + (outcome.time * outcome.probability)

        // Calculate utility
        Float utility = -expectedTime + (10 * route.safetyScore)

        // Keep track of route with maximum utility
        IF utility > maxUtility THEN
            maxUtility = utility
            bestRoute = route
            bestRoute.expectedTime = expectedTime
        END IF
    END FOR

    PRINT "Selected route: " + bestRoute.name + " | Utility: " + maxUtility

    // --- Step 3: Monitor delivery progress ---
    Float startTime = GetCurrentTime()
    Float expectedFinishTime = startTime + bestRoute.expectedTime

    WHILE IsDeliveryInProgress():

        // Check for path blockages
        IF GetPerceptionModule().IsPathBlocked(bestRoute) THEN
            PRINT "Path blocked — recalculating route..."
            SelectAndMonitorRoute(GetUpdatedRoutes(), delayThreshold)
            RETURN
        END IF

        // Check for delays beyond threshold
        Float currentTime = GetCurrentTime()
        Float remainingTime = GetWorldModel().EstimateRemainingTime(bestRoute)
        Float totalTime = (currentTime - startTime) + remainingTime
        Float currentDelay = totalTime - bestRoute.expectedTime

        IF currentDelay > delayThreshold THEN
            PRINT "Delay threshold exceeded — recalculating route..."
            SelectAndMonitorRoute(GetUpdatedRoutes(), delayThreshold)
            RETURN
        END IF

        Sleep(1) 
    END WHILE

    PRINT "Delivery complete!"
END FUNCTION
