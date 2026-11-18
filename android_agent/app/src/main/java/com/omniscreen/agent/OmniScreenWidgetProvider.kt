package com.omniscreen.agent

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.widget.RemoteViews
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class OmniScreenWidgetProvider : AppWidgetProvider() {

    companion object {
        const val ACTION_WIDGET_REFRESH = "com.omniscreen.agent.ACTION_WIDGET_REFRESH"

        fun refreshAllWidgets(context: Context) {
            try {
                val manager = AppWidgetManager.getInstance(context)
                val component = ComponentName(context, OmniScreenWidgetProvider::class.java)
                val ids = manager.getAppWidgetIds(component)
                if (ids.isNotEmpty()) {
                    for (id in ids) {
                        updateSingleWidget(context, manager, id)
                    }
                }
            } catch (_: Exception) {
                // Widget manager unavailable
            }
        }

        private fun formatMins(seconds: Double): String {
            val totalMins = Math.round(seconds / 60.0).toInt()
            val hours = totalMins / 60
            val mins = totalMins % 60
            return if (hours > 0) "${hours}h ${mins}m" else "${mins}m"
        }

        fun updateSingleWidget(
            context: Context,
            appWidgetManager: AppWidgetManager,
            appWidgetId: Int
        ) {
            val views = RemoteViews(context.packageName, R.layout.widget_omniscreen)

            // 1. Tap anywhere on widget -> open MainActivity
            val openIntent = Intent(context, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            }
            val openPending = PendingIntent.getActivity(
                context,
                0,
                openIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
            views.setOnClickPendingIntent(R.id.widget_root, openPending)

            // 2. Tap Refresh pill -> refresh local usage & cached combined reality immediately
            val refreshIntent = Intent(context, OmniScreenWidgetProvider::class.java).apply {
                action = ACTION_WIDGET_REFRESH
            }
            val refreshPending = PendingIntent.getBroadcast(
                context,
                1,
                refreshIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
            views.setOnClickPendingIntent(R.id.widget_refresh_btn, refreshPending)

            // 3. Populate local phone screen time (works 100% offline)
            try {
                val (intervals, topApps) = UsageExtractor.extractTodayUsage(context)
                val totalSec = UsageExtractor.calculateMergedSeconds(intervals)
                views.setTextViewText(R.id.widget_phone_time, formatMins(totalSec))

                val topSummary = if (topApps.isNotEmpty()) {
                    topApps.take(2).joinToString(" · ") { "${it.appName} ${formatMins(it.seconds)}" }
                } else {
                    "No app usage yet"
                }
                views.setTextViewText(R.id.widget_top_apps, topSummary)
            } catch (_: Exception) {
                views.setTextViewText(R.id.widget_phone_time, "--")
                views.setTextViewText(R.id.widget_top_apps, "Open app to grant access")
            }

            // 4. Populate Combined All-Devices exposure from last on-demand Wi-Fi sync today
            val cached = HubSyncWorker.getCachedRealityForToday(context)
            if (cached != null) {
                val (reality, syncTs) = cached
                val trueFmt = reality.optString("true_exposure_formatted", "--")
                val overlapFmt = reality.optString("second_screening_formatted", "0m")
                val ssiVal = reality.optDouble("ssi_percent", 0.0)
                val ssiColorHex = reality.optString("ssi_color", "#30D158")

                views.setTextViewText(R.id.widget_combined_time, trueFmt)
                views.setTextViewText(R.id.widget_ssi_text, "Overlap $overlapFmt · $ssiVal% SSI")
                val parsedColor = try {
                    Color.parseColor(ssiColorHex)
                } catch (_: Exception) {
                    Color.parseColor("#30D158")
                }
                views.setTextColor(R.id.widget_ssi_text, parsedColor)

                val timeStr = if (syncTs > 0L) {
                    "Synced ${SimpleDateFormat("h:mm a", Locale.getDefault()).format(Date(syncTs))}"
                } else {
                    "Synced today"
                }
                views.setTextViewText(R.id.widget_sync_time, timeStr)
            } else {
                views.setTextViewText(R.id.widget_combined_time, "--")
                views.setTextViewText(R.id.widget_ssi_text, "Tap to sync on Wi-Fi")
                views.setTextColor(R.id.widget_ssi_text, Color.parseColor("#8E8E93"))
                views.setTextViewText(R.id.widget_sync_time, "Local only")
            }

            appWidgetManager.updateAppWidget(appWidgetId, views)
        }
    }

    override fun onUpdate(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetIds: IntArray
    ) {
        for (appWidgetId in appWidgetIds) {
            updateSingleWidget(context, appWidgetManager, appWidgetId)
        }
    }

    override fun onReceive(context: Context, intent: Intent) {
        super.onReceive(context, intent)
        if (intent.action == ACTION_WIDGET_REFRESH) {
            refreshAllWidgets(context)
        }
    }
}
