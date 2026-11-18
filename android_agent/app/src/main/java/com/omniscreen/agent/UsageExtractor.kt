package com.omniscreen.agent

import android.app.usage.UsageEvents
import android.app.usage.UsageStatsManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import java.util.Calendar

data class SessionInterval(
    val startTs: Double,
    val endTs: Double,
    val appName: String,
    val category: String = "screen_on"
)

data class AppUsageSummary(
    val appName: String,
    val seconds: Double
)

object UsageExtractor {

    private val STATIC_EXCLUDED_PACKAGES = setOf(
        "",
        "android",
        "com.android.systemui",
        "com.sec.android.app.launcher",
        "com.google.android.apps.nexuslauncher",
        "com.samsung.android.app.aodservice",
        "com.samsung.android.honeyboard",
        "com.google.android.inputmethod.latin",
        "com.google.android.permissioncontroller",
        "com.android.permissioncontroller",
        "com.samsung.android.biometrics.app.setting",
        "com.android.packageinstaller",
        "com.google.android.packageinstaller",
        "com.samsung.android.app.smartcapture"
    )

    fun getStartOfDayMs(): Long {
        val calendar = Calendar.getInstance().apply {
            set(Calendar.HOUR_OF_DAY, 0)
            set(Calendar.MINUTE, 0)
            set(Calendar.SECOND, 0)
            set(Calendar.MILLISECOND, 0)
        }
        return calendar.timeInMillis
    }

    private fun getInstalledLauncherPackages(pm: PackageManager): Set<String> {
        return try {
            val homeIntent = Intent(Intent.ACTION_MAIN).apply {
                addCategory(Intent.CATEGORY_HOME)
            }
            pm.queryIntentActivities(homeIntent, 0)
                .mapNotNull { it.activityInfo?.packageName }
                .toSet()
        } catch (e: Exception) {
            emptySet()
        }
    }

    /**
     * Computes exact mathematical interval union duration in seconds so overlapping
     * transitions are never double-counted.
     */
    fun calculateMergedSeconds(intervals: List<SessionInterval>): Double {
        if (intervals.isEmpty()) return 0.0
        val sorted = intervals.filter { it.endTs > it.startTs }.sortedBy { it.startTs }
        if (sorted.isEmpty()) return 0.0

        var total = 0.0
        var currStart = sorted[0].startTs
        var currEnd = sorted[0].endTs

        for (i in 1 until sorted.size) {
            val next = sorted[i]
            if (next.startTs <= currEnd) {
                if (next.endTs > currEnd) {
                    currEnd = next.endTs
                }
            } else {
                total += (currEnd - currStart)
                currStart = next.startTs
                currEnd = next.endTs
            }
        }
        total += (currEnd - currStart)
        return total
    }

    /**
     * Extracts exact today-only foreground app screen time intervals matching
     * Samsung Digital Wellbeing and Google Digital Wellbeing.
     *
     * Key accuracy rules:
     * 1. Strictly uses UsageEvents (never bucket-aligned queryAndAggregateUsageStats,
     *    which leaks previous-day buckets into today).
     * 2. Tracks active Activity components per package so navigating between screens
     *    inside the same app (e.g., Instagram feed -> post, WhatsApp list -> chat)
     *    never prematurely closes the app session.
     * 3. Excludes Lock Screen, Home Launchers, Always-On Display, and system overlays
     *    exactly as Digital Wellbeing does.
     * 4. Clamps midnight-spanning sessions strictly to [00:00:00 today, now].
     */
    fun extractTodayUsage(context: Context): Pair<List<SessionInterval>, List<AppUsageSummary>> {
        val usm = context.getSystemService(Context.USAGE_STATS_SERVICE) as? UsageStatsManager
            ?: return Pair(emptyList(), emptyList())

        val startOfDayMs = getStartOfDayMs()
        val nowMs = System.currentTimeMillis()
        val pm = context.packageManager

        val excludedPackages = STATIC_EXCLUDED_PACKAGES + getInstalledLauncherPackages(pm)

        fun isExcluded(pkg: String): Boolean {
            if (pkg in excludedPackages) return true
            val low = pkg.lowercase()
            if (low.contains("launcher") || low.contains("systemui") || low.contains("aodservice")) {
                return true
            }
            return false
        }

        val labelCache = mutableMapOf<String, String>()
        fun resolveAppName(pkg: String): String {
            labelCache[pkg]?.let { return it }
            val resolved = try {
                val appInfo = pm.getApplicationInfo(pkg, 0)
                pm.getApplicationLabel(appInfo).toString().trim().ifEmpty { pkg }
            } catch (e: Exception) {
                // Clean readable fallback if package was uninstalled
                val parts = pkg.split(".")
                val candidate = if (parts.size >= 2 && (parts.last() == "android" || parts.last() == "app")) {
                    parts[parts.size - 2]
                } else {
                    parts.last()
                }
                candidate.replaceFirstChar { if (it.isLowerCase()) it.titlecase() else it.toString() }
            }
            labelCache[pkg] = resolved
            return resolved
        }

        // Look back 6 hours before midnight ONLY to capture sessions open across 00:00:00
        val queryStartMs = startOfDayMs - (6 * 3600 * 1000L)
        val events = usm.queryEvents(queryStartMs, nowMs)
        val event = UsageEvents.Event()

        val intervals = mutableListOf<SessionInterval>()
        val appDurationMs = mutableMapOf<String, Long>()

        var isScreenOn = false
        var activePkg: String? = null
        var activeStartMs: Long = -1L
        val resumedActivities = mutableSetOf<String>()

        fun closeActiveSession(endMs: Long) {
            val pkg = activePkg
            val startMs = activeStartMs
            if (pkg != null && startMs > 0L && endMs > startMs) {
                val clampedStart = maxOf(startMs, startOfDayMs)
                val clampedEnd = minOf(endMs, nowMs)
                if (clampedEnd > clampedStart) {
                    val deltaMs = clampedEnd - clampedStart
                    if (deltaMs >= 1000L) {
                        val appName = resolveAppName(pkg)
                        intervals.add(
                            SessionInterval(
                                startTs = clampedStart / 1000.0,
                                endTs = clampedEnd / 1000.0,
                                appName = appName,
                                category = "screen_on"
                            )
                        )
                        appDurationMs[appName] = appDurationMs.getOrDefault(appName, 0L) + deltaMs
                    }
                }
            }
            activePkg = null
            activeStartMs = -1L
            resumedActivities.clear()
        }

        while (events.hasNextEvent()) {
            events.getNextEvent(event)
            val type = event.eventType
            val time = event.timeStamp
            val pkg = event.packageName ?: ""
            val cls = event.className ?: ""

            when (type) {
                UsageEvents.Event.SCREEN_INTERACTIVE -> {
                    isScreenOn = true
                }

                UsageEvents.Event.SCREEN_NON_INTERACTIVE -> {
                    isScreenOn = false
                    closeActiveSession(time)
                }

                UsageEvents.Event.KEYGUARD_SHOWN -> {
                    closeActiveSession(time)
                }

                26 -> { // UsageEvents.Event.DEVICE_SHUTDOWN
                    isScreenOn = false
                    closeActiveSession(time)
                }

                UsageEvents.Event.ACTIVITY_RESUMED -> {
                    isScreenOn = true
                    if (isExcluded(pkg)) {
                        // User switched to Home Screen / Lock Screen / System overlay
                        closeActiveSession(time)
                    } else if (activePkg == pkg) {
                        // Another Activity inside the same app resumed seamlessly
                        if (cls.isNotEmpty()) {
                            resumedActivities.add(cls)
                        }
                    } else {
                        // Switched to a different foreground app
                        closeActiveSession(time)
                        activePkg = pkg
                        activeStartMs = time
                        if (cls.isNotEmpty()) {
                            resumedActivities.add(cls)
                        }
                    }
                }

                UsageEvents.Event.ACTIVITY_PAUSED, UsageEvents.Event.ACTIVITY_STOPPED -> {
                    if (activePkg == pkg) {
                        if (cls.isNotEmpty()) {
                            resumedActivities.remove(cls)
                        } else {
                            resumedActivities.clear()
                        }
                        if (resumedActivities.isEmpty()) {
                            closeActiveSession(time)
                        }
                    }
                }
            }
        }

        // Close currently open app up to the exact moment of querying
        if (isScreenOn && activePkg != null && activeStartMs > 0L) {
            closeActiveSession(nowMs)
        }

        val appSummaries = appDurationMs.entries
            .map { AppUsageSummary(it.key, it.value / 1000.0) }
            .filter { it.seconds >= 1.0 }
            .sortedByDescending { it.seconds }

        return Pair(intervals, appSummaries)
    }
}
