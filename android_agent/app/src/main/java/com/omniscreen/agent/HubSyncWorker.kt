package com.omniscreen.agent

import android.content.Context
import android.os.Build
import android.provider.Settings
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.net.ConnectException
import java.net.HttpURLConnection
import java.net.NoRouteToHostException
import java.net.SocketTimeoutException
import java.net.URL
import java.net.UnknownHostException
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.UUID

data class SyncResult(
    val success: Boolean,
    val message: String,
    val sessionsCount: Int = 0,
    val totalSeconds: Double = 0.0,
    val realityJson: JSONObject? = null
)

object HubSyncWorker {

    fun getOrGenerateStableDeviceId(context: Context): String {
        val prefs = context.getSharedPreferences("omniscreen_prefs", Context.MODE_PRIVATE)
        var deviceId = prefs.getString("stable_device_id", null)
        if (deviceId.isNullOrEmpty()) {
            val androidId = Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID) ?: ""
            deviceId = if (androidId.isNotEmpty()) {
                "android_${androidId.take(8)}"
            } else {
                "android_${UUID.randomUUID().toString().take(8)}"
            }
            prefs.edit().putString("stable_device_id", deviceId).apply()
        }
        return deviceId
    }

    fun getResolvedDeviceName(context: Context): String {
        val prefs = context.getSharedPreferences("omniscreen_prefs", Context.MODE_PRIVATE)
        val customName = prefs.getString("custom_device_name", "")?.trim()
        if (!customName.isNullOrEmpty()) {
            return customName
        }

        val systemName = try {
            Settings.Global.getString(context.contentResolver, "device_name")
        } catch (e: Exception) {
            null
        }

        if (!systemName.isNullOrEmpty() && !systemName.startsWith("SM-", ignoreCase = true)) {
            return systemName
        }

        val manufacturer = Build.MANUFACTURER?.replaceFirstChar {
            if (it.isLowerCase()) it.titlecase() else it.toString()
        } ?: "Android"
        return if (manufacturer.equals("samsung", ignoreCase = true)) {
            "Galaxy Phone"
        } else {
            "$manufacturer Phone"
        }
    }

    fun normalizeHostPort(raw: String): String {
        var clean = raw.trim()
            .removePrefix("http://")
            .removePrefix("https://")
            .substringBefore("/")
            .trim()
        if (clean.isNotEmpty() && !clean.contains(":")) {
            clean = "$clean:8765"
        }
        return clean
    }

    /**
     * Checks whether an active OmniScreen Reality Hub is reachable at rawHostPort.
     * Returns the PC's friendly display name (e.g. "PC (mamba)" or custom name) on success, or null if unreachable.
     */
    fun fetchHubPcName(rawHostPort: String, timeoutMs: Int = 700): String? {
        val cleanHost = normalizeHostPort(rawHostPort)
        if (cleanHost.isEmpty()) return null
        var conn: HttpURLConnection? = null
        return try {
            val url = URL("http://$cleanHost/api/status")
            conn = (url.openConnection() as HttpURLConnection).apply {
                requestMethod = "GET"
                connectTimeout = timeoutMs
                readTimeout = timeoutMs
                setRequestProperty("Accept", "application/json")
            }
            if (conn.responseCode == 200) {
                val body = BufferedReader(InputStreamReader(conn.inputStream)).use { it.readText() }
                if (body.contains("OmniScreen Reality Hub")) {
                    val json = JSONObject(body)
                    val pcName = json.optString("pc_name", "").trim()
                    if (pcName.isNotEmpty()) pcName else "PC Hub"
                } else {
                    null
                }
            } else {
                null
            }
        } catch (e: Exception) {
            null
        } finally {
            conn?.disconnect()
        }
    }

    fun getTodayDateString(): String {
        return SimpleDateFormat("yyyy-MM-dd", Locale.US).format(Date())
    }

    /**
     * Returns the last on-demand synced Combined Reality snapshot ONLY if it belongs to today.
     * Prevents stale previous-day numbers from displaying on a new morning before syncing.
     */
    fun getCachedRealityForToday(context: Context): Pair<JSONObject, Long>? {
        val prefs = context.getSharedPreferences("omniscreen_prefs", Context.MODE_PRIVATE)
        val raw = prefs.getString("last_reality_json", null) ?: return null
        val syncTs = prefs.getLong("last_reality_sync_ts", 0L)
        return try {
            val obj = JSONObject(raw)
            val dateStr = obj.optString("date", "")
            if (dateStr == getTodayDateString()) {
                Pair(obj, syncTs)
            } else {
                null
            }
        } catch (e: Exception) {
            null
        }
    }

    fun syncWithHub(context: Context, rawHubAddress: String): SyncResult {
        val cleanHost = normalizeHostPort(rawHubAddress)
        if (cleanHost.isEmpty()) {
            return SyncResult(false, "Enter your PC Hub address or tap Auto-Detect PC Hub.")
        }

        val endpoint = "http://$cleanHost/api/sync"
        val (intervals, _) = UsageExtractor.extractTodayUsage(context)

        val deviceId = getOrGenerateStableDeviceId(context)
        val deviceName = getResolvedDeviceName(context)
        val startOfDaySeconds = UsageExtractor.getStartOfDayMs() / 1000.0
        val totalDurationSeconds = UsageExtractor.calculateMergedSeconds(intervals)

        var conn: HttpURLConnection? = null
        try {
            val rootJson = JSONObject().apply {
                put("device_id", deviceId)
                put("device_name", deviceName)
                put("device_type", "android")
                put("replace_day_start_ts", startOfDaySeconds)

                val sessionsArray = JSONArray()
                for (item in intervals) {
                    val sObj = JSONObject().apply {
                        put("start_ts", item.startTs)
                        put("end_ts", item.endTs)
                        put("app_name", item.appName)
                        put("category", item.category)
                    }
                    sessionsArray.put(sObj)
                }
                put("sessions", sessionsArray)
            }

            val url = URL(endpoint)
            conn = (url.openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                connectTimeout = 5000
                readTimeout = 5000
                doOutput = true
                doInput = true
                setRequestProperty("Content-Type", "application/json")
                setRequestProperty("Accept", "application/json")
            }

            OutputStreamWriter(conn.outputStream, "UTF-8").use { writer ->
                writer.write(rootJson.toString())
                writer.flush()
            }

            val responseCode = conn.responseCode
            return if (responseCode == 200) {
                val responseBody = try {
                    BufferedReader(InputStreamReader(conn.inputStream)).use { it.readText() }
                } catch (e: Exception) {
                    ""
                }

                val prefs = context.getSharedPreferences("omniscreen_prefs", Context.MODE_PRIVATE)
                var pcName = prefs.getString("hub_pc_name", "")?.trim().orEmpty()
                var realityObj: JSONObject? = null

                if (responseBody.isNotEmpty()) {
                    try {
                        val respJson = JSONObject(responseBody)
                        val serverPcName = respJson.optString("pc_name", "").trim()
                        if (serverPcName.isNotEmpty()) {
                            pcName = serverPcName
                            prefs.edit().putString("hub_pc_name", serverPcName).apply()
                        }
                        val rObj = respJson.optJSONObject("reality")
                        if (rObj != null) {
                            realityObj = rObj
                            prefs.edit()
                                .putString("last_reality_json", rObj.toString())
                                .putLong("last_reality_sync_ts", System.currentTimeMillis())
                                .apply()
                        }
                    } catch (_: Exception) {
                        // Ignore optional response parse errors; sync itself succeeded
                    }
                }

                val displayPc = pcName.ifEmpty { "your PC" }
                val totalMins = Math.round(totalDurationSeconds / 60.0).toInt()
                val hours = totalMins / 60
                val mins = totalMins % 60
                val formatted = if (hours > 0) "${hours}h ${mins}m" else "${mins}m"
                SyncResult(
                    success = true,
                    message = "Synced $formatted with $displayPc.",
                    sessionsCount = intervals.size,
                    totalSeconds = totalDurationSeconds,
                    realityJson = realityObj
                )
            } else {
                SyncResult(false, "PC Hub responded with error code $responseCode. Please restart OmniScreen on your PC.")
            }
        } catch (e: SocketTimeoutException) {
            return SyncResult(
                false,
                "Could not reach PC Hub at $cleanHost. Confirm OmniScreen is open on your PC and both devices share the same Wi-Fi."
            )
        } catch (e: ConnectException) {
            return SyncResult(
                false,
                "PC Hub is not accepting connections at $cleanHost. Start OmniScreen on your PC and try again."
            )
        } catch (e: NoRouteToHostException) {
            return SyncResult(
                false,
                "PC at $cleanHost is not on your current Wi-Fi network. Tap Auto-Detect PC Hub to refresh."
            )
        } catch (e: UnknownHostException) {
            return SyncResult(
                false,
                "Invalid address '$cleanHost'. Tap Auto-Detect PC Hub or scan the QR code from your PC."
            )
        } catch (e: Exception) {
            return SyncResult(
                false,
                "Could not connect to $cleanHost. Ensure OmniScreen is running on your PC and tap Auto-Detect PC Hub."
            )
        } finally {
            conn?.disconnect()
        }
    }
}
