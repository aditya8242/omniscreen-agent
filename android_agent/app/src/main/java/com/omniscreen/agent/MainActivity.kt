package com.omniscreen.agent

import android.app.Activity
import android.app.AppOpsManager
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.wifi.WifiManager
import android.os.Build
import android.os.Bundle
import android.os.Process
import android.provider.Settings
import android.view.Gravity
import android.view.View
import android.widget.*
import org.json.JSONObject
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.Inet4Address
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.NetworkInterface
import java.net.Socket
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference
import kotlin.concurrent.thread

class MainActivity : Activity() {

    private lateinit var prefs: SharedPreferences
    private lateinit var statusText: TextView
    private lateinit var hubInput: EditText
    private lateinit var syncButton: Button
    private lateinit var autoDetectButton: Button
    private lateinit var permissionCard: LinearLayout
    private lateinit var permissionButton: Button
    private lateinit var previewDurationText: TextView
    private lateinit var previewAppsText: TextView
    private lateinit var combinedTimeText: TextView
    private lateinit var combinedSyncMetaText: TextView
    private lateinit var combinedMetricsText: TextView
    private lateinit var combinedSsiBadge: TextView
    private lateinit var combinedDevicesContainer: LinearLayout

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        prefs = getSharedPreferences("omniscreen_prefs", Context.MODE_PRIVATE)

        // Apple Deep Black Canvas
        val scrollView = ScrollView(this).apply {
            setBackgroundColor(Color.parseColor("#000000"))
            isFillViewport = true
        }

        val rootLayout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(40, 60, 40, 60)
            setBackgroundColor(Color.parseColor("#000000"))
            gravity = Gravity.CENTER_HORIZONTAL
        }
        scrollView.addView(rootLayout)

        // 1. Apple Header Title & Subtitle
        val titleText = TextView(this).apply {
            text = "OmniScreen"
            textSize = 28f
            setTextColor(Color.WHITE)
            typeface = Typeface.DEFAULT_BOLD
            gravity = Gravity.CENTER
            setPadding(0, 0, 0, 4)
        }
        rootLayout.addView(titleText)

        val subtitleText = TextView(this).apply {
            text = "Cross-Device Screen Time Intelligence"
            textSize = 12f
            setTextColor(Color.parseColor("#8E8E93"))
            gravity = Gravity.CENTER
            setPadding(0, 0, 0, 36)
        }
        rootLayout.addView(subtitleText)

        // 2. Permission Alert Card (Hidden when permission is granted)
        permissionCard = createCard(Color.parseColor("#1C1C1E"), Color.parseColor("#FF453A")).apply {
            orientation = LinearLayout.VERTICAL
            visibility = View.GONE

            val pTitle = TextView(this@MainActivity).apply {
                text = "Usage Access Required"
                textSize = 14f
                setTextColor(Color.parseColor("#FF453A"))
                typeface = Typeface.DEFAULT_BOLD
            }
            addView(pTitle)

            val pDesc = TextView(this@MainActivity).apply {
                text = "OmniScreen requires Usage Access to read exact system screen-on intervals matching Digital Wellbeing."
                textSize = 12f
                setTextColor(Color.parseColor("#EBEBF5"))
                setPadding(0, 8, 0, 16)
            }
            addView(pDesc)

            permissionButton = Button(this@MainActivity).apply {
                text = "Grant Usage Access"
                background = createCapsuleDrawable(Color.parseColor("#0A84FF"), 20f)
                setTextColor(Color.WHITE)
                textSize = 13f
                typeface = Typeface.DEFAULT_BOLD
                setPadding(24, 18, 24, 18)
                setOnClickListener {
                    startActivity(Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS))
                }
            }
            addView(permissionButton)

            val restrictedNotice = TextView(this@MainActivity).apply {
                text = "Android 13/14 Notice:\nIf the toggle is greyed out ('Restricted setting'): open Settings -> Apps -> OmniScreen Agent -> tap 3 dots (top right) -> Allow restricted settings."
                textSize = 11f
                setTextColor(Color.parseColor("#FF9F0A"))
                setPadding(0, 12, 0, 0)
            }
            addView(restrictedNotice)
        }
        rootLayout.addView(permissionCard)

        // 3A. Combined Reality Card (Bidirectional All-Devices Snapshot — On-Demand Sync Only)
        val combinedCard = createCard(Color.parseColor("#141417"), Color.parseColor("#2C2C2E")).apply {
            orientation = LinearLayout.VERTICAL

            val headerRow = LinearLayout(this@MainActivity).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
            }

            val combinedLabel = TextView(this@MainActivity).apply {
                text = "COMBINED EXPOSURE (ALL DEVICES)"
                textSize = 10f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(Color.parseColor("#0A84FF"))
                layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
            }
            headerRow.addView(combinedLabel)

            combinedSyncMetaText = TextView(this@MainActivity).apply {
                text = "On-demand sync"
                textSize = 10f
                setTextColor(Color.parseColor("#8E8E93"))
            }
            headerRow.addView(combinedSyncMetaText)
            addView(headerRow)

            combinedTimeText = TextView(this@MainActivity).apply {
                text = "--"
                textSize = 34f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(Color.WHITE)
                setPadding(0, 6, 0, 4)
            }
            addView(combinedTimeText)

            combinedMetricsText = TextView(this@MainActivity).apply {
                text = "Tap Sync Reality below when on Wi-Fi to pull combined time across all devices."
                textSize = 12f
                setTextColor(Color.parseColor("#98989E"))
                setPadding(0, 0, 0, 10)
            }
            addView(combinedMetricsText)

            combinedSsiBadge = TextView(this@MainActivity).apply {
                text = ""
                textSize = 11f
                typeface = Typeface.DEFAULT_BOLD
                setPadding(20, 8, 20, 8)
                visibility = View.GONE
                val lp = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.WRAP_CONTENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
                ).apply { setMargins(0, 0, 0, 12) }
                layoutParams = lp
            }
            addView(combinedSsiBadge)

            combinedDevicesContainer = LinearLayout(this@MainActivity).apply {
                orientation = LinearLayout.VERTICAL
            }
            addView(combinedDevicesContainer)
        }
        rootLayout.addView(combinedCard)

        // 3B. This Device Live Card (Always Local, Even Offline)
        val previewCard = createCard(Color.parseColor("#1C1C1E"), Color.parseColor("#2C2C2E")).apply {
            orientation = LinearLayout.VERTICAL

            val cardLabel = TextView(this@MainActivity).apply {
                text = "THIS DEVICE TODAY (LOCAL)"
                textSize = 10f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(Color.parseColor("#8E8E93"))
            }
            addView(cardLabel)

            previewDurationText = TextView(this@MainActivity).apply {
                text = "Reading usage..."
                textSize = 28f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(Color.WHITE)
                setPadding(0, 4, 0, 6)
            }
            addView(previewDurationText)

            previewAppsText = TextView(this@MainActivity).apply {
                text = "Extracting app foreground intervals..."
                textSize = 11f
                setTextColor(Color.parseColor("#98989E"))
            }
            addView(previewAppsText)
        }
        rootLayout.addView(previewCard)

        // 4. Connection & Pairing Card
        val pairingCard = createCard(Color.parseColor("#1C1C1E"), Color.parseColor("#2C2C2E")).apply {
            orientation = LinearLayout.VERTICAL

            val devLabel = TextView(this@MainActivity).apply {
                text = "DEVICE DISPLAY NAME"
                textSize = 10f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(Color.parseColor("#8E8E93"))
                setPadding(0, 0, 0, 8)
            }
            addView(devLabel)

            val nameInput = EditText(this@MainActivity).apply {
                hint = "e.g. Galaxy Phone"
                setText(HubSyncWorker.getResolvedDeviceName(this@MainActivity))
                setTextColor(Color.WHITE)
                setHintTextColor(Color.parseColor("#636366"))
                background = createCapsuleDrawable(Color.parseColor("#2C2C2E"), 14f)
                setPadding(28, 20, 28, 20)
                textSize = 14f
                addTextChangedListener(object : android.text.TextWatcher {
                    override fun afterTextChanged(s: android.text.Editable?) {
                        val n = s?.toString()?.trim() ?: ""
                        if (n.isNotEmpty()) {
                            prefs.edit().putString("custom_device_name", n).apply()
                        }
                    }
                    override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
                    override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
                })
            }
            addView(nameInput)

            val cardLabel = TextView(this@MainActivity).apply {
                text = "PC REALITY HUB PAIRING"
                textSize = 10f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(Color.parseColor("#8E8E93"))
                setPadding(0, 18, 0, 12)
            }
            addView(cardLabel)

            // Auto-Detect 1-Tap Button
            autoDetectButton = Button(this@MainActivity).apply {
                text = "Auto-Detect PC Hub"
                background = createCapsuleDrawable(Color.parseColor("#0A84FF"), 24f)
                setTextColor(Color.WHITE)
                textSize = 13f
                typeface = Typeface.DEFAULT_BOLD
                setPadding(24, 20, 24, 20)
                setOnClickListener { triggerAutoDiscovery() }
            }
            addView(autoDetectButton)

            val orText = TextView(this@MainActivity).apply {
                text = "or scan PC QR code / enter LAN IP:"
                textSize = 11f
                setTextColor(Color.parseColor("#636366"))
                gravity = Gravity.CENTER
                setPadding(0, 14, 0, 8)
            }
            addView(orText)

            hubInput = EditText(this@MainActivity).apply {
                hint = "e.g. 10.175.204.103:8765"
                setText(prefs.getString("hub_address", "10.175.204.103:8765"))
                setTextColor(Color.WHITE)
                setHintTextColor(Color.parseColor("#636366"))
                background = createCapsuleDrawable(Color.parseColor("#2C2C2E"), 14f)
                setPadding(28, 22, 28, 22)
                textSize = 14f
            }
            addView(hubInput)
        }
        rootLayout.addView(pairingCard)

        // 5. Sync Action Button
        syncButton = Button(this).apply {
            text = "Sync Reality to PC Now"
            background = createCapsuleDrawable(Color.parseColor("#30D158"), 28f)
            setTextColor(Color.BLACK)
            textSize = 15f
            typeface = Typeface.DEFAULT_BOLD
            setPadding(32, 28, 32, 28)
            val params = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { setMargins(0, 16, 0, 16) }
            layoutParams = params
            setOnClickListener { triggerSync() }
        }
        rootLayout.addView(syncButton)

        // 6. Live Status Readout
        statusText = TextView(this).apply {
            text = "Ready to sync."
            textSize = 12f
            setTextColor(Color.parseColor("#8E8E93"))
            gravity = Gravity.CENTER
            setPadding(16, 8, 16, 16)
        }
        rootLayout.addView(statusText)

        setContentView(scrollView)
        handleIncomingPairingIntent(intent)
    }

    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        if (intent != null) {
            setIntent(intent)
            handleIncomingPairingIntent(intent)
        }
    }

    private fun handleIncomingPairingIntent(incoming: Intent?) {
        val uri = incoming?.data ?: return
        if (uri.scheme == "omniscreen" && uri.host == "pair") {
            val rawHost = uri.getQueryParameter("host") ?: return
            val normalized = HubSyncWorker.normalizeHostPort(rawHost)
            val pcName = uri.getQueryParameter("name")?.trim().orEmpty().ifEmpty { "your PC" }
            if (normalized.isNotEmpty()) {
                hubInput.setText(normalized)
                prefs.edit()
                    .putString("hub_address", normalized)
                    .putString("hub_pc_name", pcName)
                    .apply()
                statusText.text = "Connected to $pcName"
                statusText.setTextColor(Color.parseColor("#30D158"))
                Toast.makeText(this, "Connected to $pcName", Toast.LENGTH_SHORT).show()
                if (hasUsageAccess()) {
                    triggerSync()
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        updatePermissionAndPreview()
        val cached = HubSyncWorker.getCachedRealityForToday(applicationContext)
        renderCombinedReality(cached?.first, cached?.second ?: 0L)
    }

    private fun renderCombinedReality(reality: JSONObject?, syncTimestampMs: Long) {
        combinedDevicesContainer.removeAllViews()
        if (reality == null) {
            combinedTimeText.text = "--"
            combinedSyncMetaText.text = "On-demand sync"
            combinedMetricsText.text = "Tap Sync Reality below when connected to Wi-Fi to view combined exposure across all devices."
            combinedSsiBadge.visibility = View.GONE
            return
        }

        val trueFormatted = reality.optString("true_exposure_formatted", "0m")
        val rawFormatted = reality.optString("raw_total_formatted", "0m")
        val overlapFormatted = reality.optString("second_screening_formatted", "0m")
        val ssiPercent = reality.optDouble("ssi_percent", 0.0)
        val ssiStatus = reality.optString("ssi_status", "Optimal Focus")
        val ssiColorHex = reality.optString("ssi_color", "#30D158")

        combinedTimeText.text = trueFormatted
        combinedSyncMetaText.text = if (syncTimestampMs > 0L) {
            "Synced ${SimpleDateFormat("h:mm a", Locale.getDefault()).format(Date(syncTimestampMs))}"
        } else {
            "Synced today"
        }
        combinedMetricsText.text = "Raw Sum: $rawFormatted   |   2nd-Screening: $overlapFormatted"

        val parsedColor = try {
            Color.parseColor(ssiColorHex)
        } catch (_: Exception) {
            Color.parseColor("#30D158")
        }
        val bgAlphaColor = Color.argb(38, Color.red(parsedColor), Color.green(parsedColor), Color.blue(parsedColor))
        combinedSsiBadge.text = "$ssiPercent% $ssiStatus"
        combinedSsiBadge.setTextColor(parsedColor)
        combinedSsiBadge.background = createCapsuleDrawable(bgAlphaColor, 999f)
        combinedSsiBadge.visibility = View.VISIBLE

        val devices = reality.optJSONArray("devices") ?: return
        for (i in 0 until devices.length()) {
            val dev = devices.optJSONObject(i) ?: continue
            val devName = dev.optString("device_name", "Device")
            val devType = dev.optString("device_type", "").uppercase(Locale.US)
            val devFormatted = dev.optString("formatted", "0m")

            val rowCard = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                background = createCapsuleDrawable(Color.parseColor("#1C1C20"), 18f)
                setPadding(24, 18, 24, 18)
                val lp = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
                ).apply { setMargins(0, 10, 0, 0) }
                layoutParams = lp
            }

            val topLine = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
            }

            val nameView = TextView(this).apply {
                text = if (devType.isNotEmpty()) "$devName  ($devType)" else devName
                textSize = 13f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(Color.WHITE)
                layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
            }
            topLine.addView(nameView)

            val durView = TextView(this).apply {
                text = devFormatted
                textSize = 14f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(Color.parseColor("#30D158"))
            }
            topLine.addView(durView)
            rowCard.addView(topLine)

            val topApps = dev.optJSONArray("top_apps")
            if (topApps != null && topApps.length() > 0) {
                val appParts = mutableListOf<String>()
                val limit = minOf(3, topApps.length())
                for (j in 0 until limit) {
                    val appObj = topApps.optJSONObject(j) ?: continue
                    val appName = appObj.optString("app_name", "")
                    val appFmt = appObj.optString("formatted", "0m")
                    if (appName.isNotEmpty()) {
                        appParts.add("$appName ($appFmt)")
                    }
                }
                if (appParts.isNotEmpty()) {
                    val appsView = TextView(this).apply {
                        text = appParts.joinToString("  |  ")
                        textSize = 11f
                        setTextColor(Color.parseColor("#8E8E93"))
                        setPadding(0, 6, 0, 0)
                    }
                    rowCard.addView(appsView)
                }
            }

            combinedDevicesContainer.addView(rowCard)
        }
    }

    private fun createCard(bgColor: Int, borderColor: Int): LinearLayout {
        return LinearLayout(this).apply {
            val drawable = GradientDrawable().apply {
                setColor(bgColor)
                cornerRadius = 32f
                setStroke(2, borderColor)
            }
            background = drawable
            setPadding(36, 32, 36, 32)
            val params = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { setMargins(0, 0, 0, 24) }
            layoutParams = params
        }
    }

    private fun createCapsuleDrawable(fillColor: Int, radius: Float): GradientDrawable {
        return GradientDrawable().apply {
            setColor(fillColor)
            cornerRadius = radius
        }
    }

    private fun hasUsageAccess(): Boolean {
        val appOps = getSystemService(Context.APP_OPS_SERVICE) as? AppOpsManager ?: return false
        val mode = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            appOps.unsafeCheckOpNoThrow(
                AppOpsManager.OPSTR_GET_USAGE_STATS,
                Process.myUid(),
                packageName
            )
        } else {
            appOps.checkOpNoThrow(
                AppOpsManager.OPSTR_GET_USAGE_STATS,
                Process.myUid(),
                packageName
            )
        }
        return mode == AppOpsManager.MODE_ALLOWED
    }

    private fun updatePermissionAndPreview() {
        val granted = hasUsageAccess()
        if (granted) {
            permissionCard.visibility = View.GONE
            syncButton.isEnabled = true
            loadUsagePreview()
        } else {
            permissionCard.visibility = View.VISIBLE
            syncButton.isEnabled = false
            previewDurationText.text = "Permission required"
            previewAppsText.text = "Grant Usage Access above to extract real screen time."
        }
    }

    private fun formatMinutes(seconds: Double): String {
        val totalMins = Math.round(seconds / 60.0).toInt()
        val hours = totalMins / 60
        val mins = totalMins % 60
        return if (hours > 0) "${hours}h ${mins}m" else "${mins}m"
    }

    private fun loadUsagePreview() {
        thread {
            val (intervals, topApps) = UsageExtractor.extractTodayUsage(applicationContext)
            val totalSec = UsageExtractor.calculateMergedSeconds(intervals)
            val formattedTotal = formatMinutes(totalSec)

            val appsSummary = if (topApps.isNotEmpty()) {
                topApps.take(3).joinToString("  |  ") {
                    "${it.appName} (${formatMinutes(it.seconds)})"
                }
            } else {
                "No active foreground apps today yet."
            }

            runOnUiThread {
                previewDurationText.text = formattedTotal
                previewAppsText.text = appsSummary
            }
        }
    }

    private fun triggerAutoDiscovery() {
        statusText.text = "Searching local Wi-Fi and hotspot for PC Reality Hub..."
        statusText.setTextColor(Color.parseColor("#0A84FF"))
        autoDetectButton.isEnabled = false

        val currentCandidate = hubInput.text.toString().trim()

        thread {
            val discovered = discoverPcHubOnLan(currentCandidate)
            runOnUiThread {
                autoDetectButton.isEnabled = true
                if (discovered != null) {
                    val (addr, pcName) = discovered
                    hubInput.setText(addr)
                    prefs.edit()
                        .putString("hub_address", addr)
                        .putString("hub_pc_name", pcName)
                        .apply()
                    statusText.text = "Connected to $pcName"
                    statusText.setTextColor(Color.parseColor("#30D158"))
                    Toast.makeText(this, "Connected to $pcName", Toast.LENGTH_SHORT).show()
                } else {
                    statusText.text = "No PC Hub found on this Wi-Fi. Confirm OmniScreen is open on your PC, then retry or scan the QR code."
                    statusText.setTextColor(Color.parseColor("#FF9F0A"))
                }
            }
        }
    }

    /**
     * Collects active private IPv4 addresses and broadcast addresses across Wi-Fi and Mobile Hotspot interfaces.
     */
    private fun collectLocalIpv4Interfaces(): Pair<List<String>, List<InetAddress>> {
        val localIps = mutableListOf<String>()
        val broadcasts = mutableListOf<InetAddress>()
        try {
            val interfaces = NetworkInterface.getNetworkInterfaces() ?: return Pair(localIps, broadcasts)
            for (nif in interfaces) {
                if (!nif.isUp || nif.isLoopback) continue
                for (ia in nif.interfaceAddresses) {
                    val addr = ia.address
                    if (addr is Inet4Address && !addr.isLoopbackAddress) {
                        val ip = addr.hostAddress ?: continue
                        if (isPrivateLanIp(ip)) {
                            localIps.add(ip)
                            ia.broadcast?.let { broadcasts.add(it) }
                        }
                    }
                }
            }
        } catch (e: Exception) {
            // Ignore interface enumeration errors
        }
        return Pair(localIps, broadcasts)
    }

    private fun isPrivateLanIp(ip: String): Boolean {
        return ip.startsWith("192.168.") || ip.startsWith("10.") ||
            (ip.startsWith("172.") && (ip.split(".").getOrNull(1)?.toIntOrNull() in 16..31))
    }

    /**
     * Bulletproof 2-Stage PC Hub Discovery:
     *   0. Fast check of currently saved/entered address (<500ms).
     *   1. UDP broadcast across all Wi-Fi + Hotspot subnet broadcast addresses AND 255.255.255.255.
     *   2. Parallel TCP port 8765 sweep on local /24 subnet (succeeds even when Windows Firewall blocks UDP 8766!).
     * Returns Pair(hostPort, pcFriendlyName) or null.
     */
    private fun discoverPcHubOnLan(savedCandidate: String): Pair<String, String>? {
        // Stage 0: Fast verification of currently saved address
        val normalizedSaved = HubSyncWorker.normalizeHostPort(savedCandidate)
        if (normalizedSaved.isNotEmpty()) {
            val pcName = HubSyncWorker.fetchHubPcName(normalizedSaved, 500)
            if (pcName != null) {
                return Pair(normalizedSaved, pcName)
            }
        }

        val (localIps, broadcasts) = collectLocalIpv4Interfaces()

        // Stage 1: Multi-interface UDP Broadcast Probe (Port 8766)
        val udpResult = probeViaUdp(broadcasts)
        if (udpResult != null) {
            val pcName = HubSyncWorker.fetchHubPcName(udpResult.first, 600) ?: udpResult.second
            return Pair(udpResult.first, pcName)
        }

        // Stage 2: Parallel TCP Port 8765 Subnet Sweep (immune to UDP 8766 firewall blocks)
        return probeViaSubnetTcpSweep(localIps)
    }

    private fun probeViaUdp(broadcasts: List<InetAddress>): Pair<String, String>? {
        var multicastLock: WifiManager.MulticastLock? = null
        var socket: DatagramSocket? = null
        try {
            val wifi = applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager
            multicastLock = wifi?.createMulticastLock("omniscreen_discovery")?.apply {
                setReferenceCounted(true)
                acquire()
            }

            socket = DatagramSocket().apply {
                broadcast = true
                soTimeout = 1000
            }

            val targets = linkedSetOf<InetAddress>()
            targets.addAll(broadcasts)
            targets.add(InetAddress.getByName("255.255.255.255"))

            val msg = "OMNISCREEN_DISCOVER".toByteArray()
            for (target in targets) {
                try {
                    socket.send(DatagramPacket(msg, msg.size, target, 8766))
                } catch (e: Exception) {
                    // Continue probing remaining targets
                }
            }

            val buf = ByteArray(1024)
            val reply = DatagramPacket(buf, buf.size)
            socket.receive(reply)
            val text = String(reply.data, 0, reply.length).trim()

            if (text.startsWith("OMNISCREEN_OFFER|")) {
                val parts = text.split("|")
                if (parts.size >= 3) {
                    val hostPort = "${parts[1]}:${parts[2]}"
                    val fallbackName = if (parts.size >= 4 && parts[3].isNotBlank()) parts[3] else "PC Hub"
                    return Pair(hostPort, fallbackName)
                }
            }
        } catch (e: Exception) {
            // Fall through to Stage 2 TCP sweep
        } finally {
            try { socket?.close() } catch (_: Exception) {}
            try { multicastLock?.release() } catch (_: Exception) {}
        }
        return null
    }

    private fun probeViaSubnetTcpSweep(localIps: List<String>): Pair<String, String>? {
        val prefixes = localIps.mapNotNull { ip ->
            val parts = ip.split(".")
            if (parts.size == 4) "${parts[0]}.${parts[1]}.${parts[2]}." else null
        }.distinct()

        if (prefixes.isEmpty()) return null

        val found = AtomicReference<Pair<String, String>?>(null)
        val executor = Executors.newFixedThreadPool(48)

        try {
            for (prefix in prefixes) {
                for (host in 1..254) {
                    val candidateIp = "$prefix$host"
                    if (localIps.contains(candidateIp)) continue
                    executor.execute {
                        if (found.get() != null) return@execute
                        var sock: Socket? = null
                        try {
                            sock = Socket()
                            sock.connect(InetSocketAddress(candidateIp, 8765), 320)
                            sock.close()
                            val addr = "$candidateIp:8765"
                            val pcName = HubSyncWorker.fetchHubPcName(addr, 600)
                            if (pcName != null) {
                                found.compareAndSet(null, Pair(addr, pcName))
                            }
                        } catch (_: Exception) {
                            // Host closed or unreachable
                        } finally {
                            try { sock?.close() } catch (_: Exception) {}
                        }
                    }
                }
            }
            executor.shutdown()
            executor.awaitTermination(3500, TimeUnit.MILLISECONDS)
        } catch (_: Exception) {
            // Timeout reached
        } finally {
            executor.shutdownNow()
        }

        return found.get()
    }

    private fun triggerSync() {
        val address = hubInput.text.toString().trim()
        if (address.isEmpty()) {
            Toast.makeText(this, "Tap Auto-Detect PC Hub or enter PC address", Toast.LENGTH_SHORT).show()
            return
        }

        val normalized = HubSyncWorker.normalizeHostPort(address)
        hubInput.setText(normalized)
        prefs.edit().putString("hub_address", normalized).apply()

        statusText.text = "Syncing exact screen time intervals to PC..."
        statusText.setTextColor(Color.parseColor("#0A84FF"))
        syncButton.isEnabled = false

        thread {
            val result = HubSyncWorker.syncWithHub(applicationContext, normalized)
            runOnUiThread {
                syncButton.isEnabled = true
                if (result.success) {
                    statusText.text = result.message
                    statusText.setTextColor(Color.parseColor("#30D158"))
                    Toast.makeText(this, "Sync Complete", Toast.LENGTH_SHORT).show()
                    if (result.realityJson != null) {
                        renderCombinedReality(result.realityJson, System.currentTimeMillis())
                    }
                    loadUsagePreview()
                    OmniScreenWidgetProvider.refreshAllWidgets(applicationContext)
                } else {
                    statusText.text = result.message
                    statusText.setTextColor(Color.parseColor("#FF453A"))
                }
            }
        }
    }
}
