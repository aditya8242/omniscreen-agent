# OmniScreen Reality Hub - Apple macOS Sequoia & iOS Screen Time Design
# Designed strictly to Apple Human Interface Guidelines standards (zero emojis)

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>OmniScreen Reality Hub</title>
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <style>
    :root {
      --bg: #000000;
      --card-bg: #141417;
      --card-secondary: #1C1C20;
      --card-border: rgba(255, 255, 255, 0.08);
      --card-hover: rgba(255, 255, 255, 0.04);
      --text-main: #FFFFFF;
      --text-secondary: #8E8E93;
      --text-muted: #636366;
      --blue: #0A84FF;
      --blue-hover: #0071E3;
      --green: #30D158;
      --orange: #FF9F0A;
      --purple: #BF5AF2;
      --red: #FF453A;
      --font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      -webkit-font-smoothing: antialiased;
    }

    body {
      background-color: var(--bg);
      color: var(--text-main);
      font-family: var(--font-family);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 24px 16px 40px;
      user-select: none;
    }

    .container {
      width: 100%;
      max-width: 500px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    /* Apple Navigation Bar */
    .nav-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0 4px 6px;
    }

    .nav-brand {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .brand-icon {
      width: 30px;
      height: 30px;
      border-radius: 8px;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 2px 10px rgba(10, 132, 255, 0.28);
    }

    .nav-title {
      font-size: 20px;
      font-weight: 700;
      letter-spacing: -0.4px;
    }

    .live-status-pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(48, 209, 88, 0.12);
      border: 1px solid rgba(48, 209, 88, 0.28);
      color: var(--green);
      font-size: 11px;
      font-weight: 600;
      padding: 5px 12px;
      border-radius: 999px;
      letter-spacing: 0.2px;
      transition: all 0.2s ease;
    }

    .live-status-pill.offline {
      background: rgba(255, 69, 58, 0.14);
      border-color: rgba(255, 69, 58, 0.35);
      color: var(--red);
    }

    .pulse-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--green);
      box-shadow: 0 0 8px var(--green);
      animation: pulse 2s infinite ease-in-out;
    }

    .live-status-pill.offline .pulse-dot {
      background: var(--red);
      box-shadow: 0 0 8px var(--red);
      animation: none;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.35; transform: scale(0.85); }
    }

    /* Apple Cards */
    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 20px;
      padding: 20px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
      position: relative;
    }

    .card-header-label {
      font-size: 11px;
      font-weight: 700;
      color: var(--text-muted);
      letter-spacing: 0.8px;
      text-transform: uppercase;
      margin-bottom: 6px;
    }

    /* Hero Gauge Card */
    .hero-card {
      text-align: center;
      padding: 24px 20px 22px;
      display: flex;
      flex-direction: column;
      align-items: center;
    }

    .hero-dial-wrap {
      position: relative;
      width: 176px;
      height: 176px;
      margin: 8px auto 12px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .hero-dial-svg {
      transform: rotate(-90deg);
      width: 176px;
      height: 176px;
    }

    .hero-dial-bg {
      fill: none;
      stroke: rgba(255, 255, 255, 0.05);
      stroke-width: 14;
    }

    .hero-dial-fill {
      fill: none;
      stroke: url(#heroGradient);
      stroke-width: 14;
      stroke-linecap: round;
      stroke-dasharray: 452;
      stroke-dashoffset: 452;
      transition: stroke-dashoffset 0.9s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .hero-time-center {
      position: absolute;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
    }

    .hero-time-val {
      font-size: 36px;
      font-weight: 800;
      letter-spacing: -1px;
      line-height: 1;
    }

    .hero-sub-text {
      font-size: 12px;
      color: var(--text-secondary);
      margin-top: 4px;
    }

    /* 2-Column Metric Strip */
    .metric-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }

    .metric-box {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 16px;
    }

    .metric-box-title {
      font-size: 11px;
      font-weight: 700;
      color: var(--text-muted);
      letter-spacing: 0.6px;
      text-transform: uppercase;
      margin-bottom: 4px;
    }

    .metric-box-value {
      font-size: 22px;
      font-weight: 700;
      letter-spacing: -0.5px;
    }

    .text-orange { color: var(--orange); }
    .text-purple { color: var(--purple); }
    .text-blue { color: var(--blue); }
    .text-green { color: var(--green); }

    /* Cognitive Attention / SSI Strip */
    .ssi-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 16px 18px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .ssi-top-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
    }

    .ssi-label {
      font-size: 11px;
      font-weight: 700;
      color: var(--text-muted);
      letter-spacing: 0.6px;
      text-transform: uppercase;
    }

    .ssi-badge {
      font-size: 11px;
      font-weight: 700;
      padding: 3px 10px;
      border-radius: 999px;
      letter-spacing: 0.2px;
      white-space: nowrap;
    }

    .ssi-desc {
      font-size: 12px;
      color: var(--text-secondary);
      line-height: 1.4;
    }

    /* Section Headers */
    .section-title-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 4px;
      padding: 0 4px;
    }

    .section-title {
      font-size: 11px;
      font-weight: 700;
      color: var(--text-muted);
      letter-spacing: 0.8px;
      text-transform: uppercase;
    }

    .section-actions {
      display: flex;
      align-items: center;
      gap: 14px;
    }

    .text-action-link {
      font-size: 12px;
      color: var(--blue);
      text-decoration: none;
      font-weight: 600;
      cursor: pointer;
    }

    .text-action-link:hover {
      text-decoration: underline;
    }

    /* Device Fleet List */
    .device-list {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .device-row {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      transition: background 0.15s, border-color 0.15s;
    }

    .device-row:hover {
      background: rgba(255, 255, 255, 0.02);
      border-color: rgba(255, 255, 255, 0.12);
    }

    .device-top-line {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .device-name-wrap {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .device-icon-badge {
      width: 34px;
      height: 34px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .badge-pc { background: rgba(10, 132, 255, 0.15); color: var(--blue); }
    .badge-phone { background: rgba(191, 90, 242, 0.15); color: var(--purple); }
    .badge-tv { background: rgba(255, 159, 10, 0.15); color: var(--orange); }

    .device-name {
      font-size: 15px;
      font-weight: 600;
      letter-spacing: -0.2px;
    }

    .device-duration {
      font-size: 16px;
      font-weight: 700;
      letter-spacing: -0.3px;
    }

    .device-apps-pills {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 2px;
    }

    .app-pill {
      background: rgba(255, 255, 255, 0.06);
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 11px;
      color: var(--text-secondary);
      font-weight: 500;
    }

    .device-meta-actions {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 4px;
      padding-top: 6px;
      border-top: 1px solid rgba(255, 255, 255, 0.04);
    }

    .btn-meta {
      background: none;
      border: none;
      color: var(--text-secondary);
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
      padding: 4px 9px;
      border-radius: 6px;
      font-family: inherit;
      transition: background 0.15s, color 0.15s;
    }

    .btn-meta:hover {
      color: var(--text-main);
      background: rgba(255, 255, 255, 0.08);
    }

    .btn-meta.btn-danger:hover {
      color: var(--red);
      background: rgba(255, 69, 58, 0.12);
    }

    /* Smart TV Card */
    .tv-card {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .tv-status-badge {
      font-size: 11px;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 6px;
      white-space: nowrap;
    }
    .tv-online { background: rgba(48, 209, 88, 0.15); color: var(--green); }
    .tv-offline { background: rgba(255, 255, 255, 0.06); color: var(--text-muted); }

    /* Primary Action Button */
    .btn-primary {
      background: var(--blue);
      color: #FFFFFF;
      border: none;
      border-radius: 14px;
      padding: 15px 20px;
      font-size: 15px;
      font-weight: 600;
      letter-spacing: -0.2px;
      width: 100%;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      font-family: inherit;
      box-shadow: 0 4px 16px rgba(10, 132, 255, 0.3);
      transition: background 0.15s, transform 0.05s;
    }

    .btn-primary:hover {
      background: var(--blue-hover);
    }

    .btn-primary:active {
      transform: scale(0.99);
    }

    /* Cupertino In-UI Glassmorphic Modal Dialog */
    .modal-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.65);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      padding: 20px;
      animation: modalFadeIn 0.18s ease-out;
    }

    @keyframes modalFadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    .modal-box {
      background: #1C1C1E;
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 20px;
      width: 100%;
      max-width: 380px;
      padding: 24px 22px 20px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.7);
      animation: modalScaleUp 0.18s ease-out;
    }

    @keyframes modalScaleUp {
      from { transform: scale(0.95); opacity: 0; }
      to { transform: scale(1); opacity: 1; }
    }

    .modal-title {
      font-size: 17px;
      font-weight: 700;
      letter-spacing: -0.3px;
      text-align: center;
    }

    .modal-desc {
      font-size: 13px;
      color: var(--text-secondary);
      text-align: center;
      line-height: 1.45;
    }

    .modal-input {
      background: #2C2C2E;
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 12px;
      padding: 12px 14px;
      color: #FFFFFF;
      font-size: 14px;
      font-family: inherit;
      outline: none;
      width: 100%;
    }

    .modal-input:focus {
      border-color: var(--blue);
    }

    .modal-actions {
      display: flex;
      gap: 10px;
      margin-top: 4px;
    }

    .modal-btn {
      flex: 1;
      border: none;
      border-radius: 12px;
      padding: 12px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      font-family: inherit;
      transition: background 0.15s;
    }

    .modal-btn-cancel {
      background: #2C2C2E;
      color: #FFFFFF;
    }
    .modal-btn-cancel:hover {
      background: #3A3A3C;
    }

    .modal-btn-danger {
      background: var(--red);
      color: #FFFFFF;
    }
    .modal-btn-danger:hover {
      background: #E0352A;
    }

    .modal-btn-primary {
      background: var(--blue);
      color: #FFFFFF;
    }
    .modal-btn-primary:hover {
      background: var(--blue-hover);
    }

    /* QR Code Display in Modal */
    .qr-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 12px;
    }

    .qr-image-frame {
      background: #FFFFFF;
      padding: 12px;
      border-radius: 16px;
      width: 186px;
      height: 186px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #1C1C1E;
      font-size: 12px;
      text-align: center;
    }

    .qr-image-frame img {
      width: 162px;
      height: 162px;
      display: block;
    }

    .qr-address-badge {
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 13px;
      color: var(--green);
      background: rgba(48, 209, 88, 0.1);
      border: 1px solid rgba(48, 209, 88, 0.25);
      padding: 6px 14px;
      border-radius: 8px;
      user-select: all;
    }

    /* Apple Pill Toast Notification */
    .toast-pill {
      position: fixed;
      bottom: 24px;
      background: rgba(28, 28, 30, 0.96);
      border: 1px solid rgba(255, 255, 255, 0.15);
      color: #FFFFFF;
      font-size: 13px;
      font-weight: 500;
      padding: 10px 18px;
      border-radius: 999px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      display: flex;
      align-items: center;
      gap: 8px;
      z-index: 2000;
      opacity: 0;
      transform: translateY(20px);
      pointer-events: none;
      transition: opacity 0.25s cubic-bezier(0.16, 1, 0.3, 1), transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .toast-pill.visible {
      opacity: 1;
      transform: translateY(0);
    }

    /* Footer */
    .footer-note {
      text-align: center;
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 6px;
      line-height: 1.5;
    }
  </style>
</head>
<body>

  <div class="container">

    <!-- 1. Navigation Header -->
    <div class="nav-bar">
      <div class="nav-brand">
        <div class="brand-icon" aria-hidden="true">
          <svg width="30" height="30" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg">
            <rect x="0" y="0" width="512" height="512" rx="120" fill="#14141A"/>
            <circle cx="204" cy="256" r="118" fill="none" stroke="#0A84FF" stroke-width="44"/>
            <circle cx="308" cy="256" r="118" fill="none" stroke="#BF5AF2" stroke-width="44"/>
            <circle cx="256" cy="256" r="28" fill="#30D158"/>
          </svg>
        </div>
        <div class="nav-title">OmniScreen Reality</div>
      </div>
      <div id="hubStatusPill" class="live-status-pill">
        <span class="pulse-dot"></span>
        <span id="hubStatusText">Live Sync</span>
      </div>
    </div>

    <!-- 2. Hero Screen Time Gauge -->
    <div class="card hero-card">
      <div class="card-header-label">True Combined Screen Exposure</div>

      <div class="hero-dial-wrap">
        <svg class="hero-dial-svg" viewBox="0 0 176 176">
          <defs>
            <linearGradient id="heroGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#0A84FF"/>
              <stop offset="50%" stop-color="#BF5AF2"/>
              <stop offset="100%" stop-color="#30D158"/>
            </linearGradient>
          </defs>
          <circle class="hero-dial-bg" cx="88" cy="88" r="72"/>
          <circle id="heroDialProgress" class="hero-dial-fill" cx="88" cy="88" r="72"/>
        </svg>
        <div class="hero-time-center">
          <div id="heroTime" class="hero-time-val">0m</div>
        </div>
      </div>

      <div id="heroSub" class="hero-sub-text">Interval union across active devices today</div>
    </div>

    <!-- 3. Metric Comparison Grid -->
    <div class="metric-grid">
      <div class="metric-box">
        <div class="metric-box-title">Raw Screen Sum</div>
        <div id="metricRaw" class="metric-box-value">0m</div>
      </div>
      <div class="metric-box">
        <div class="metric-box-title text-orange">2nd-Screening</div>
        <div id="metricOverlap" class="metric-box-value text-orange">0m</div>
      </div>
    </div>

    <!-- 4. Cognitive Attention & SSI Card -->
    <div class="ssi-card">
      <div class="ssi-top-row">
        <div class="ssi-label">Attention Fragmentation Index</div>
        <div id="ssiBadge" class="ssi-badge" style="background: rgba(48, 209, 88, 0.15); color: var(--green);">0.0% Optimal Focus</div>
      </div>
      <div id="ssiDescription" class="ssi-desc">
        Calculating multi-screen simultaneous exposure...
      </div>
    </div>

    <!-- 5. Connected Devices Section -->
    <div class="section-title-row">
      <div class="section-title">Connected Devices</div>
      <a class="text-action-link" onclick="openPairingModal()">+ Pair Mobile</a>
    </div>

    <div id="deviceList" class="device-list">
      <div style="text-align: center; color: var(--text-muted); padding: 18px; font-size: 13px;">
        Loading connected devices...
      </div>
    </div>

    <!-- 6. Smart TV Entertainment Hub -->
    <div class="section-title-row">
      <div class="section-title">Smart TV Entertainment</div>
      <div class="section-actions">
        <a class="text-action-link" onclick="openAddTvModal()">+ Add IP</a>
        <a class="text-action-link" onclick="scanNetworkTvs()">Scan Wi-Fi</a>
      </div>
    </div>

    <div class="card tv-card" id="tvCardContainer">
      <div style="display: flex; justify-content: space-between; align-items: center; gap: 8px;">
        <div style="display: flex; align-items: center; gap: 10px;">
          <div class="device-icon-badge badge-tv" style="width: 30px; height: 30px; border-radius: 8px;">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="2" y="4" width="20" height="14" rx="2"></rect>
              <line x1="8" y1="21" x2="16" y2="21"></line>
              <line x1="12" y1="18" x2="12" y2="21"></line>
            </svg>
          </div>
          <span id="tvName" style="font-size: 14px; font-weight: 600;">Smart TV Monitor</span>
        </div>
        <span id="tvStatusBadge" class="tv-status-badge tv-offline">Not Configured</span>
      </div>
      <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.45;" id="tvDetails">
        Click Scan Wi-Fi while your Smart TV is turned on, or add its local IP manually.
      </div>
    </div>

    <!-- 7. Primary Action Button -->
    <button id="btnCalculate" class="btn-primary" onclick="calculateReality()">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="23 4 23 10 17 10"></polyline>
        <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
      </svg>
      <span id="btnText">Calculate Reality</span>
    </button>

    <!-- Footer -->
    <div class="footer-note">
      OmniScreen Reality Hub &bull; Local Wi-Fi Network &bull; Zero External Telemetry
    </div>

  </div>

  <!-- Custom Cupertino Delete Confirmation Modal -->
  <div id="deleteModal" class="modal-overlay" onclick="handleBackdropClick(event, closeDeleteModal)">
    <div class="modal-box">
      <div class="modal-title">Remove Device?</div>
      <div class="modal-desc" id="deleteModalDesc">
        Are you sure you want to remove this device and its recorded screen time sessions from Reality Hub?
      </div>
      <div class="modal-actions">
        <button class="modal-btn modal-btn-cancel" onclick="closeDeleteModal()">Cancel</button>
        <button class="modal-btn modal-btn-danger" id="btnConfirmDelete" onclick="confirmDeleteDevice()">Remove</button>
      </div>
    </div>
  </div>

  <!-- Custom Cupertino Rename Modal -->
  <div id="renameModal" class="modal-overlay" onclick="handleBackdropClick(event, closeRenameModal)">
    <div class="modal-box">
      <div class="modal-title">Rename Device</div>
      <div class="modal-desc">
        Enter a clean display name for this device (for example, "Galaxy Phone" or "Workstation"):
      </div>
      <input type="text" id="renameInput" class="modal-input" placeholder="Device Name" onkeydown="if(event.key==='Enter') confirmRenameDevice()">
      <div class="modal-actions">
        <button class="modal-btn modal-btn-cancel" onclick="closeRenameModal()">Cancel</button>
        <button class="modal-btn modal-btn-primary" onclick="confirmRenameDevice()">Save Name</button>
      </div>
    </div>
  </div>

  <!-- Custom Cupertino Manual Smart TV Modal -->
  <div id="addTvModal" class="modal-overlay" onclick="handleBackdropClick(event, closeAddTvModal)">
    <div class="modal-box">
      <div class="modal-title">Add Smart TV</div>
      <div class="modal-desc">
        Enter your Smart TV's local Wi-Fi IP address (found in TV Network Settings):
      </div>
      <input type="text" id="tvNameInput" class="modal-input" placeholder="Name (e.g. Living Room TV)">
      <input type="text" id="tvIpInput" class="modal-input" placeholder="IP Address (e.g. 192.168.1.50)" onkeydown="if(event.key==='Enter') confirmAddTv()">
      <div class="modal-actions">
        <button class="modal-btn modal-btn-cancel" onclick="closeAddTvModal()">Cancel</button>
        <button class="modal-btn modal-btn-primary" onclick="confirmAddTv()">Add TV</button>
      </div>
    </div>
  </div>

  <!-- Custom Cupertino Pairing & Local QR Modal -->
  <div id="pairingModal" class="modal-overlay" onclick="handleBackdropClick(event, closePairingModal)">
    <div class="modal-box">
      <div class="modal-title">1-Tap Mobile Pairing</div>
      <div class="modal-desc">
        <b>Option 1:</b> Open OmniScreen on Android and tap <b>Auto-Detect PC Hub</b>.<br>
        <b>Option 2:</b> Scan this QR code with your phone camera to pair instantly over Wi-Fi:
      </div>
      <div class="qr-container">
        <div class="qr-image-frame" id="qrFrame">
          <img id="localQrImg" src="" alt="Local Wi-Fi Pairing QR Code" onerror="handleQrError()">
        </div>
        <div id="modalLanIpBadge" class="qr-address-badge">Detecting Wi-Fi IP...</div>
      </div>
      <div class="modal-actions">
        <button class="modal-btn modal-btn-cancel" onclick="copyLanAddress()">Copy Address</button>
        <button class="modal-btn modal-btn-primary" onclick="closePairingModal()">Done</button>
      </div>
    </div>
  </div>

  <!-- Apple Pill Toast Notification -->
  <div id="toastPill" class="toast-pill">
    <span id="toastIcon"></span>
    <span id="toastMsg">Action complete</span>
  </div>

  <script>
    let isFetching = false;
    let pendingDeleteDeviceId = null;
    let pendingRenameDeviceId = null;
    let currentLanIp = "127.0.0.1:8765";
    let devicesById = {};
    let toastTimer = null;

    const SVG_CHECK = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#30D158" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>';
    const SVG_ALERT = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#FF453A" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>';
    const SVG_PC = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line></svg>';
    const SVG_PHONE = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="2" width="14" height="20" rx="2.5"></rect><line x1="12" y1="18" x2="12.01" y2="18"></line></svg>';
    const SVG_TV = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="14" rx="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="18" x2="12" y2="21"></line></svg>';

    function showToast(msg, isError = false) {
      const toast = document.getElementById("toastPill");
      const icon = document.getElementById("toastIcon");
      const text = document.getElementById("toastMsg");

      icon.innerHTML = isError ? SVG_ALERT : SVG_CHECK;
      text.innerText = msg;

      toast.classList.add("visible");
      if (toastTimer) clearTimeout(toastTimer);
      toastTimer = setTimeout(() => {
        toast.classList.remove("visible");
      }, 3000);
    }

    function setHubOnlineState(isOnline) {
      const pill = document.getElementById("hubStatusPill");
      const text = document.getElementById("hubStatusText");
      if (isOnline) {
        pill.classList.remove("offline");
        text.innerText = "Live Sync";
      } else {
        pill.classList.add("offline");
        text.innerText = "Hub Offline";
      }
    }

    function handleBackdropClick(event, closeFn) {
      if (event.target === event.currentTarget) {
        closeFn();
      }
    }

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        closeDeleteModal();
        closeRenameModal();
        closePairingModal();
        closeAddTvModal();
      }
    });

    async function calculateReality(silent = false) {
      if (isFetching) return;
      isFetching = true;
      const btn = document.getElementById("btnCalculate");
      const btnText = document.getElementById("btnText");
      if (!silent) {
        btn.style.opacity = "0.75";
        btnText.innerText = "Calculating Reality...";
      }

      try {
        const res = await fetch("/api/reality", { cache: "no-store" });
        if (res.ok) {
          const data = await res.json();
          setHubOnlineState(true);
          renderReality(data);
        } else {
          setHubOnlineState(false);
          if (!silent) showToast("Unable to read metrics from Reality Hub.", true);
        }
      } catch (e) {
        setHubOnlineState(false);
        if (!silent) showToast("Reality Hub is offline. Restart OmniScreen on your PC.", true);
      } finally {
        isFetching = false;
        btn.style.opacity = "1";
        btnText.innerText = "Calculate Reality";
      }
    }

    function renderReality(data) {
      document.getElementById("heroTime").innerText = data.true_exposure_formatted || "0m";
      const count = data.device_count || 0;
      document.getElementById("heroSub").innerText = `Interval union across ${count} active device${count === 1 ? '' : 's'} today`;
      document.getElementById("metricRaw").innerText = data.raw_total_formatted || "0m";
      document.getElementById("metricOverlap").innerText = data.second_screening_formatted || "0m";

      if (data.lan_ip) {
        currentLanIp = `${data.lan_ip}:8765`;
        document.getElementById("modalLanIpBadge").innerText = currentLanIp;
      }

      const ssiBadge = document.getElementById("ssiBadge");
      const ssiDesc = document.getElementById("ssiDescription");
      const ssiVal = data.ssi_percent !== undefined ? data.ssi_percent : 0.0;
      const ssiStatus = data.ssi_status || "Optimal Focus";
      const ssiColor = data.ssi_color || "#30D158";

      ssiBadge.innerText = `${ssiVal}% ${ssiStatus}`;
      ssiBadge.style.color = ssiColor;
      ssiBadge.style.background = `${ssiColor}22`;
      ssiDesc.innerText = data.ssi_description || "Calculated from cross-device interval intersection math.";

      const trueSec = data.true_exposure_seconds || 0;
      const ratio = Math.min(1.0, trueSec / (8 * 3600));
      const offset = 452 - (ratio * 350);
      document.getElementById("heroDialProgress").style.strokeDashoffset = offset;

      renderDevices(data.devices || []);
    }

    function renderDevices(devices) {
      const container = document.getElementById("deviceList");
      devicesById = {};

      if (!devices || devices.length === 0) {
        container.innerHTML = `
          <div style="text-align: center; color: var(--text-muted); padding: 18px; font-size: 13px;">
            No device activity recorded today yet.
          </div>`;
        return;
      }

      container.innerHTML = devices.map((dev, idx) => {
        devicesById[dev.device_id] = dev;
        const type = (dev.device_type || "pc").toLowerCase();
        const badgeClass = type === "pc" ? "badge-pc" : (type === "tv" ? "badge-tv" : "badge-phone");
        const icon = type === "pc" ? SVG_PC : (type === "tv" ? SVG_TV : SVG_PHONE);
        const apps = (dev.top_apps || []).slice(0, 3).map(a =>
          `<span class="app-pill">${escapeHtml(a.app_name)} (${escapeHtml(a.formatted)})</span>`
        ).join("");

        return `
          <div class="device-row">
            <div class="device-top-line">
              <div class="device-name-wrap">
                <div class="device-icon-badge ${badgeClass}">${icon}</div>
                <div>
                  <div class="device-name">${escapeHtml(dev.device_name)}</div>
                  <div style="font-size: 11px; color: var(--text-muted);">${escapeHtml(type.toUpperCase())}</div>
                </div>
              </div>
              <div class="device-duration">${escapeHtml(dev.formatted)}</div>
            </div>
            ${apps ? `<div class="device-apps-pills">${apps}</div>` : ''}
            <div class="device-meta-actions">
              <span>ID: ${escapeHtml(dev.device_id)}</span>
              <div>
                <button class="btn-meta" data-action="rename" data-id="${escapeHtml(dev.device_id)}">Rename</button>
                <button class="btn-meta btn-danger" data-action="delete" data-id="${escapeHtml(dev.device_id)}">Remove</button>
              </div>
            </div>
          </div>
        `;
      }).join("");

      container.querySelectorAll("button[data-action]").forEach(btn => {
        btn.addEventListener("click", () => {
          const did = btn.getAttribute("data-id");
          const dev = devicesById[did];
          const dname = dev ? dev.device_name : did;
          if (btn.getAttribute("data-action") === "rename") {
            openRenameModal(did, dname);
          } else {
            openDeleteModal(did, dname);
          }
        });
      });
    }

    function openDeleteModal(deviceId, deviceName) {
      pendingDeleteDeviceId = deviceId;
      document.getElementById("deleteModalDesc").innerText =
        `Remove "${deviceName}" and all of its recorded screen time sessions from Reality Hub?`;
      document.getElementById("deleteModal").style.display = "flex";
    }

    function closeDeleteModal() {
      pendingDeleteDeviceId = null;
      document.getElementById("deleteModal").style.display = "none";
    }

    async function confirmDeleteDevice() {
      if (!pendingDeleteDeviceId) return;
      const did = pendingDeleteDeviceId;
      closeDeleteModal();

      try {
        const res = await fetch(`/api/device/delete?device_id=${encodeURIComponent(did)}`, { method: "POST" });
        const body = await res.json().catch(() => ({}));
        if (res.ok) {
          showToast("Device removed successfully.");
          calculateReality(true);
        } else {
          showToast(body.detail || "Could not remove this device.", true);
        }
      } catch (e) {
        showToast("Cannot reach Reality Hub. Make sure OmniScreen is running.", true);
      }
    }

    function openRenameModal(deviceId, currentName) {
      pendingRenameDeviceId = deviceId;
      const input = document.getElementById("renameInput");
      input.value = currentName;
      document.getElementById("renameModal").style.display = "flex";
      setTimeout(() => {
        input.focus();
        input.select();
      }, 40);
    }

    function closeRenameModal() {
      pendingRenameDeviceId = null;
      document.getElementById("renameModal").style.display = "none";
    }

    async function confirmRenameDevice() {
      if (!pendingRenameDeviceId) return;
      const did = pendingRenameDeviceId;
      const newName = document.getElementById("renameInput").value.trim();
      if (!newName) {
        showToast("Please enter a device name.", true);
        return;
      }
      closeRenameModal();

      try {
        const res = await fetch(`/api/device/rename?device_id=${encodeURIComponent(did)}&new_name=${encodeURIComponent(newName)}`, { method: "POST" });
        const body = await res.json().catch(() => ({}));
        if (res.ok) {
          showToast(`Renamed device to "${newName}".`);
          calculateReality(true);
        } else {
          showToast(body.detail || "Could not rename device.", true);
        }
      } catch (e) {
        showToast("Cannot reach Reality Hub. Make sure OmniScreen is running.", true);
      }
    }

    async function openPairingModal() {
      const frame = document.getElementById("qrFrame");
      frame.innerHTML = `<img id="localQrImg" src="/api/qr?t=${Date.now()}" alt="Local Wi-Fi Pairing QR Code" onerror="handleQrError()">`;
      document.getElementById("pairingModal").style.display = "flex";

      try {
        const res = await fetch("/api/status", { cache: "no-store" });
        if (res.ok) {
          const st = await res.json();
          if (st.lan_ip) {
            currentLanIp = `${st.lan_ip}:${st.hub_port || 8765}`;
          }
          document.getElementById("modalLanIpBadge").innerText = currentLanIp;
          setHubOnlineState(true);
        }
      } catch (e) {
        setHubOnlineState(false);
        document.getElementById("modalLanIpBadge").innerText = "Hub Offline";
      }
    }

    function handleQrError() {
      const frame = document.getElementById("qrFrame");
      frame.innerHTML = `<div style="padding: 12px; color: #1C1C1E; font-weight: 600;">QR unavailable while Reality Hub is offline. Restart OmniScreen.</div>`;
    }

    function closePairingModal() {
      document.getElementById("pairingModal").style.display = "none";
    }

    function copyLanAddress() {
      if (navigator.clipboard) {
        navigator.clipboard.writeText(currentLanIp).then(() => {
          showToast(`Copied ${currentLanIp}`);
        }).catch(() => {
          showToast(`Hub Address: ${currentLanIp}`);
        });
      } else {
        showToast(`Hub Address: ${currentLanIp}`);
      }
    }

    function openAddTvModal() {
      document.getElementById("tvNameInput").value = "";
      document.getElementById("tvIpInput").value = "";
      document.getElementById("addTvModal").style.display = "flex";
      setTimeout(() => document.getElementById("tvIpInput").focus(), 40);
    }

    function closeAddTvModal() {
      document.getElementById("addTvModal").style.display = "none";
    }

    async function confirmAddTv() {
      const name = document.getElementById("tvNameInput").value.trim();
      const ip = document.getElementById("tvIpInput").value.trim();
      if (!ip) {
        showToast("Please enter the Smart TV IP address.", true);
        return;
      }
      try {
        const res = await fetch("/api/tv/add", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ device_name: name || null, ip_address: ip })
        });
        const body = await res.json().catch(() => ({}));
        if (res.ok) {
          closeAddTvModal();
          showToast(body.message || "Smart TV added.");
          loadTvStatus();
        } else {
          showToast(body.detail || "Could not add Smart TV.", true);
        }
      } catch (e) {
        showToast("Cannot reach Reality Hub.", true);
      }
    }

    async function scanNetworkTvs() {
      const badge = document.getElementById("tvStatusBadge");
      const details = document.getElementById("tvDetails");
      badge.className = "tv-status-badge tv-online";
      badge.innerText = "Scanning Wi-Fi...";
      details.innerText = "Probing SSDP and Smart TV ports on your local network...";

      try {
        const res = await fetch("/api/tv/scan", { method: "POST" });
        if (res.ok) {
          const data = await res.json();
          if (data.count > 0) {
            badge.innerText = `Found ${data.count} TV(s)`;
            details.innerText = `Monitoring: ${data.discovered.map(d => d.device_name).join(', ')}`;
            showToast(`Discovered ${data.count} Smart TV device(s) on Wi-Fi.`);
            loadTvStatus();
          } else {
            badge.className = "tv-status-badge tv-offline";
            badge.innerText = "No TV Found";
            details.innerText = "Ensure your TV is powered on and on the same Wi-Fi, or tap + Add IP.";
            showToast("No active Smart TVs answered on Wi-Fi.");
          }
        } else {
          badge.className = "tv-status-badge tv-offline";
          badge.innerText = "Scan Failed";
          showToast("Smart TV scan could not complete.", true);
        }
      } catch (e) {
        badge.className = "tv-status-badge tv-offline";
        badge.innerText = "Hub Offline";
        showToast("Reality Hub is offline.", true);
      }
    }

    async function loadTvStatus() {
      try {
        const res = await fetch("/api/tv/status", { cache: "no-store" });
        if (res.ok) {
          const data = await res.json();
          const tvs = data.tvs || [];
          const badge = document.getElementById("tvStatusBadge");
          const details = document.getElementById("tvDetails");
          if (tvs.length > 0) {
            const onlineTv = tvs.find(t => t.is_online);
            if (onlineTv) {
              badge.className = "tv-status-badge tv-online";
              badge.innerText = "Active (Streaming)";
              details.innerText = `${onlineTv.device_name} (${onlineTv.ip_address}) is actively on.`;
            } else {
              badge.className = "tv-status-badge tv-offline";
              badge.innerText = "Standby (Screen Off)";
              details.innerText = `Monitoring ${tvs.length} Smart TV(s): ${tvs.map(t => t.device_name).join(', ')}.`;
            }
          } else {
            badge.className = "tv-status-badge tv-offline";
            badge.innerText = "Not Configured";
            details.innerText = "Click Scan Wi-Fi while your Smart TV is turned on, or add its local IP manually.";
          }
        }
      } catch (e) {}
    }

    function escapeHtml(str) {
      if (str === null || str === undefined) return "";
      return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
    }

    // Initial load and silent background refresh
    calculateReality(true);
    loadTvStatus();
    setInterval(() => calculateReality(true), 10000);
    setInterval(loadTvStatus, 20000);
  </script>
</body>
</html>
"""
