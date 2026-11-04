"use strict";

document.documentElement.classList.add("js-ready");

// API configuration: same-origin when served by FastAPI, or fallback to dev port 8000
const API_BASE = window.AQUASENSE_API_BASE
  || (window.location.protocol === "file:" || window.location.port === "5500" ? "http://127.0.0.1:8000" : window.location.origin);
const LOW_THRESHOLD = 20;
const SVG_NS = "http://www.w3.org/2000/svg";
const ISO_TIMESTAMP_REGEX = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/;

const elements = {
  // Banners & State
  loading: document.querySelector("#loading-state"),
  error: document.querySelector("#error-state"),
  errorMessage: document.querySelector("#error-message"),
  staleBanner: document.querySelector("#stale-state"),
  staleMessage: document.querySelector("#stale-message"),
  cachedBanner: document.querySelector("#cached-state"),
  cachedMessage: document.querySelector("#cached-message"),
  cachedRetry: document.querySelector("#cached-retry-button"),
  grid: document.querySelector("#metric-grid"),
  refresh: document.querySelector("#refresh-button"),
  retry: document.querySelector("#retry-button"),
  connection: document.querySelector("#connection-status"),
  connectionLabel: document.querySelector("#connection-label"),
  liveBeacon: document.querySelector("#live-beacon"),
  eyebrowText: document.querySelector("#eyebrow-text"),
  deviceStatusTag: document.querySelector("#device-status-tag"),
  apiFooterStatus: document.querySelector("#api-footer-status"),
  
  // Gauges & Levels
  gauge: document.querySelector("#level-gauge"),
  current: document.querySelector("#current-level"),
  currentCaption: document.querySelector("#current-caption"),
  levelStatus: document.querySelector("#level-status"),
  minimum: document.querySelector("#minimum-level"),
  maximum: document.querySelector("#maximum-level"),
  updated: document.querySelector("#last-updated"),
  tankLiquidFill: document.querySelector("#tank-liquid-fill"),
  systemHealthDot: document.querySelector("#system-health-dot"),
  systemHealthText: document.querySelector("#system-health-text"),

  // Alerts & Events
  activeAlerts: document.querySelector("#active-alerts"),
  activeCount: document.querySelector("#active-count"),
  events: document.querySelector("#historical-events"),
  eventCount: document.querySelector("#event-count"),

  // Chart
  chartWrap: document.querySelector("#chart-wrap"),
  chart: document.querySelector("#history-chart"),
  chartGrid: document.querySelector("#chart-grid"),
  chartThreshold: document.querySelector("#chart-threshold"),
  chartArea: document.querySelector("#chart-area"),
  chartLine: document.querySelector("#chart-line"),
  chartPoints: document.querySelector("#chart-points"),
  chartLabels: document.querySelector("#chart-labels"),
  chartEmpty: document.querySelector("#chart-empty"),
  chartTooltip: document.querySelector("#chart-tooltip"),
  tooltipTime: document.querySelector("#tooltip-time"),
  tooltipVal: document.querySelector("#tooltip-val"),

  // Welcome Screen
  welcomeScreen: document.querySelector("#welcome-screen"),
  enterDashboardBtn: document.querySelector("#enter-dashboard-btn"),
  welcomeTimerFill: document.querySelector("#welcome-timer-fill"),
  welcomeCountdown: document.querySelector("#welcome-countdown"),
  replayIntroBtn: document.querySelector("#replay-intro-btn"),
  themeToggleBtn: document.querySelector("#theme-toggle-btn"),
  welcomeParticles: document.querySelector("#welcome-particles"),
};

// ==========================================================================
// STATE MANAGEMENT & DATA CACHE
// ==========================================================================

let lastValidSummary = null;
let activeDashboardController = null;
let cachedAuthToken = (() => {
  try {
    return sessionStorage.getItem("aquasense_token") || null;
  } catch (_) {
    return null;
  }
})();

// ==========================================================================
// STRICT PAYLOAD VALIDATION FUNCTIONS
// ==========================================================================

function evaluateAlertThreshold(level) {
  const num = Number(level);
  if (!Number.isFinite(num)) {
    throw new TypeError("Tank level must be a finite number");
  }
  return num < LOW_THRESHOLD;
}

function validateTankReading(reading, index = 0) {
  if (!reading || typeof reading !== "object") {
    throw new Error(`Reading at index ${index} must be a valid object.`);
  }

  if (typeof reading.timestamp !== "string" || !ISO_TIMESTAMP_REGEX.test(reading.timestamp)) {
    throw new Error(`Reading at index ${index} has an invalid or missing ISO timestamp: "${reading.timestamp}".`);
  }

  const parsedTime = new Date(reading.timestamp).getTime();
  if (Number.isNaN(parsedTime)) {
    throw new Error(`Reading at index ${index} has an unparseable timestamp: "${reading.timestamp}".`);
  }

  const rawLevel = reading.level !== undefined ? reading.level : reading.level_percent;
  if (rawLevel === undefined || rawLevel === null || typeof rawLevel === "boolean") {
    throw new Error(`Reading at index ${index} has a missing or invalid level.`);
  }

  const level = Number(rawLevel);
  if (!Number.isFinite(level) || level < 0 || level > 100) {
    throw new Error(`Reading at index ${index} level must be between 0 and 100, received: ${rawLevel}.`);
  }

  return {
    timestamp: reading.timestamp,
    level,
  };
}

function validateTankSummary(summary) {
  if (!summary || typeof summary !== "object") {
    throw new Error("Tank summary response must be an object.");
  }

  const currentLevel = Number(summary.current_level);
  if (!Number.isFinite(currentLevel) || currentLevel < 0 || currentLevel > 100) {
    throw new Error(`Tank summary current_level must be a number between 0 and 100, received: ${summary.current_level}.`);
  }

  const minLevel = Number(summary.minimum_level);
  if (!Number.isFinite(minLevel) || minLevel < 0 || minLevel > 100) {
    throw new Error(`Tank summary minimum_level must be a number between 0 and 100, received: ${summary.minimum_level}.`);
  }

  const maxLevel = Number(summary.maximum_level);
  if (!Number.isFinite(maxLevel) || maxLevel < 0 || maxLevel > 100) {
    throw new Error(`Tank summary maximum_level must be a number between 0 and 100, received: ${summary.maximum_level}.`);
  }

  if (minLevel > maxLevel) {
    throw new Error(`Tank summary minimum_level (${minLevel}) cannot exceed maximum_level (${maxLevel}).`);
  }

  if (typeof summary.active_alert !== "boolean") {
    throw new Error(`Tank summary active_alert must be a boolean, received: ${typeof summary.active_alert}.`);
  }

  if (!Array.isArray(summary.readings)) {
    throw new Error("Tank summary readings must be an array.");
  }

  const validatedReadings = summary.readings.map((r, i) => validateTankReading(r, i));

  // Check monotonic chronological ordering
  for (let i = 1; i < validatedReadings.length; i++) {
    const prevTime = new Date(validatedReadings[i - 1].timestamp).getTime();
    const currTime = new Date(validatedReadings[i].timestamp).getTime();
    if (currTime < prevTime) {
      throw new Error(`Readings are not in chronological order: index ${i} is earlier than index ${i - 1}.`);
    }
  }

  let validatedEvents = [];
  if (Array.isArray(summary.historical_low_events)) {
    validatedEvents = summary.historical_low_events.map((e, i) => validateTankReading(e, i));
  }

  let latestTimestamp = null;
  if (summary.latest_reading_timestamp !== null && summary.latest_reading_timestamp !== undefined) {
    if (typeof summary.latest_reading_timestamp !== "string" || !ISO_TIMESTAMP_REGEX.test(summary.latest_reading_timestamp)) {
      throw new Error(`Invalid latest_reading_timestamp: "${summary.latest_reading_timestamp}".`);
    }
    latestTimestamp = summary.latest_reading_timestamp;
  } else if (validatedReadings.length > 0) {
    latestTimestamp = validatedReadings[validatedReadings.length - 1].timestamp;
  }

  const isStale = summary.is_stale !== undefined ? Boolean(summary.is_stale) : false;

  return {
    current_level: currentLevel,
    minimum_level: minLevel,
    maximum_level: maxLevel,
    active_alert: summary.active_alert,
    readings: validatedReadings,
    historical_low_events: validatedEvents,
    is_stale: isStale,
    latest_reading_timestamp: latestTimestamp,
  };
}

function validateDeviceStatus(data) {
  if (!data || typeof data !== "object") {
    throw new Error("Device status response must be an object.");
  }

  const id = data.id || data.device_id;
  if (typeof id !== "string" || id.trim() === "") {
    throw new Error("Device status must have a non-empty string ID.");
  }

  if (typeof data.online !== "boolean") {
    throw new Error(`Device status online field must be boolean, received: ${typeof data.online}.`);
  }

  if (typeof data.last_seen !== "string" || !ISO_TIMESTAMP_REGEX.test(data.last_seen)) {
    throw new Error(`Device status last_seen must be an ISO timestamp, received: "${data.last_seen}".`);
  }

  const rawLevel = data.level_percent !== undefined ? data.level_percent : data.level;
  if (rawLevel !== undefined && rawLevel !== null && typeof rawLevel !== "boolean") {
    const level = Number(rawLevel);
    if (!Number.isFinite(level) || level < 0 || level > 100) {
      throw new Error(`Device level_percent must be between 0 and 100, received: ${rawLevel}.`);
    }
  }

  if (data.pump_state !== undefined && data.pump_state !== "on" && data.pump_state !== "off") {
    throw new Error(`Device pump_state must be 'on' or 'off', received: "${data.pump_state}".`);
  }

  return {
    id,
    online: data.online,
    last_seen: data.last_seen,
    is_stale: Boolean(data.is_stale),
    level_percent: rawLevel !== undefined ? Number(rawLevel) : 55.0,
    pump_state: data.pump_state || "off",
  };
}

// ==========================================================================
// TIME-PROPORTIONAL CHART COORDINATE ENGINE
// ==========================================================================

function calculateChartPoints(readings, chartWidth = 760, chartHeight = 280, margins = { left: 46, right: 20, top: 18, bottom: 38 }) {
  const { left, right, top, bottom } = margins;
  const plotWidth = chartWidth - left - right;
  const plotHeight = chartHeight - top - bottom;
  const yFor = (level) => top + ((100 - level) / 100) * plotHeight;

  if (!Array.isArray(readings) || readings.length === 0) {
    return [];
  }

  const timestamps = readings.map((r) => new Date(r.timestamp).getTime());
  const minTime = Math.min(...timestamps);
  const maxTime = Math.max(...timestamps);
  const timeSpan = maxTime - minTime;

  return readings.map((reading) => {
    const time = new Date(reading.timestamp).getTime();
    let x;
    if (readings.length === 1 || timeSpan <= 0) {
      x = left + plotWidth / 2;
    } else {
      x = left + ((time - minTime) / timeSpan) * plotWidth;
    }
    const y = yFor(Number(reading.level));
    return {
      x: Number(x.toFixed(2)),
      y: Number(y.toFixed(2)),
      reading,
      isUnderThreshold: Number(reading.level) < LOW_THRESHOLD,
    };
  });
}

// ==========================================================================
// WELCOME SCREEN LIFECYCLE & TRANSITIONS
// ==========================================================================

let welcomeTimer = null;
let welcomeCountdownInterval = null;
let welcomeRemainingSeconds = 3;

function initWelcomeParticles() {
  if (!elements.welcomeParticles) return;
  elements.welcomeParticles.replaceChildren();
  const particleCount = 18;
  for (let i = 0; i < particleCount; i++) {
    const p = document.createElement("div");
    p.className = "welcome-bubble-particle";
    const size = Math.floor(Math.random() * 8) + 3;
    const left = Math.floor(Math.random() * 96) + 2;
    const duration = (Math.random() * 6 + 5).toFixed(1);
    const delay = (Math.random() * 4).toFixed(1);
    p.style.cssText = `
      position: absolute;
      bottom: -15px;
      left: ${left}%;
      width: ${size}px;
      height: ${size}px;
      border-radius: 50%;
      background: rgba(56, 189, 248, ${Math.random() * 0.35 + 0.15});
      box-shadow: 0 0 8px rgba(34, 211, 238, 0.4);
      animation: bubbleRiseUp ${duration}s infinite linear;
      animation-delay: ${delay}s;
      pointer-events: none;
    `;
    elements.welcomeParticles.appendChild(p);
  }

  if (!document.querySelector("#welcome-bubble-style")) {
    const style = document.createElement("style");
    style.id = "welcome-bubble-style";
    style.textContent = `
      @keyframes bubbleRiseUp {
        0% { transform: translateY(0) scale(0.6); opacity: 0; }
        20% { opacity: 0.8; }
        90% { opacity: 0.7; }
        100% { transform: translateY(-105vh) scale(1.2); opacity: 0; }
      }
    `;
    document.head.appendChild(style);
  }
}

function dismissWelcomeScreen() {
  if (welcomeTimer) {
    window.clearTimeout(welcomeTimer);
    welcomeTimer = null;
  }
  if (welcomeCountdownInterval) {
    window.clearInterval(welcomeCountdownInterval);
    welcomeCountdownInterval = null;
  }

  if (elements.welcomeScreen) {
    elements.welcomeScreen.classList.add("is-leaving");
    window.setTimeout(() => {
      elements.welcomeScreen.hidden = true;
      triggerRevealAnimations();
    }, 650);
  }
}

function showWelcomeScreen() {
  if (!elements.welcomeScreen) return;
  elements.welcomeScreen.hidden = false;
  elements.welcomeScreen.classList.remove("is-leaving");
  startWelcomeCountdown(3);
}

function startWelcomeCountdown(seconds = 3) {
  welcomeRemainingSeconds = seconds;
  if (elements.welcomeCountdown) elements.welcomeCountdown.textContent = String(welcomeRemainingSeconds);
  if (elements.welcomeTimerFill) {
    elements.welcomeTimerFill.style.transition = "none";
    elements.welcomeTimerFill.style.width = "0%";
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        if (elements.welcomeTimerFill) {
          elements.welcomeTimerFill.style.transition = `width ${seconds}s linear`;
          elements.welcomeTimerFill.style.width = "100%";
        }
      });
    });
  }

  if (welcomeCountdownInterval) window.clearInterval(welcomeCountdownInterval);
  welcomeCountdownInterval = window.setInterval(() => {
    welcomeRemainingSeconds -= 1;
    if (elements.welcomeCountdown) {
      elements.welcomeCountdown.textContent = String(Math.max(0, welcomeRemainingSeconds));
    }
  }, 1000);

  if (welcomeTimer) window.clearTimeout(welcomeTimer);
  welcomeTimer = window.setTimeout(() => {
    dismissWelcomeScreen();
  }, seconds * 1000);
}

// ==========================================================================
// THEME SWITCHER
// ==========================================================================

function initTheme() {
  const saved = localStorage.getItem("aquasense-theme") || "dark";
  document.documentElement.setAttribute("data-theme", saved);
  updateThemeMeta(saved);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme") || "dark";
  const target = current === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", target);
  localStorage.setItem("aquasense-theme", target);
  updateThemeMeta(target);
}

function updateThemeMeta(theme) {
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) {
    meta.setAttribute("content", theme === "dark" ? "#060d17" : "#f1f7fa");
  }
}

// ==========================================================================
// CONNECTIVITY & RENDERING LOGIC
// ==========================================================================

function setConnection(state, label) {
  if (!elements.connection) return;
  elements.connection.classList.toggle("is-loading", state === "loading");
  elements.connection.classList.toggle("is-error", state === "error");
  if (elements.connectionLabel) elements.connectionLabel.textContent = label;
  if (elements.apiFooterStatus) {
    elements.apiFooterStatus.textContent = state === "error" ? "Unreachable" : "Operational";
    elements.apiFooterStatus.style.color = state === "error" ? "#fb7185" : "inherit";
  }
}

function setDeviceStatusUI(state, label) {
  if (!elements.deviceStatusTag) return;
  elements.deviceStatusTag.className = "online-tag";
  if (state === "offline") elements.deviceStatusTag.classList.add("offline");
  else if (state === "stale") elements.deviceStatusTag.classList.add("stale");
  else if (state === "unknown") elements.deviceStatusTag.classList.add("unknown");
  elements.deviceStatusTag.textContent = label;
}

function formatPercent(value) {
  return `${Number.isInteger(value) ? value : Number(value.toFixed(1))}%`;
}

function formatTimestamp(value, options = {}) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown time";
  return new Intl.DateTimeFormat(undefined, options).format(date);
}

function setPercentStat(element, value) {
  if (!element) return;
  const number = Number(value);
  const unit = document.createElement("span");
  unit.textContent = "%";
  element.replaceChildren(document.createTextNode(formatPercent(number).replace("%", "")), unit);
}

function svgElement(name, attributes = {}, text = "") {
  const node = document.createElementNS(SVG_NS, name);
  Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value));
  if (text) node.textContent = text;
  return node;
}

// ==========================================================================
// METRIC RENDERING & FRESHNESS VISUALIZATION
// ==========================================================================

function renderMetrics(summary) {
  const current = Number(summary.current_level);
  const isLow = Boolean(summary.active_alert);
  const isStale = Boolean(summary.is_stale);

  // Circular Radial Gauge
  if (elements.current) elements.current.textContent = formatPercent(current);
  if (elements.currentCaption) elements.currentCaption.textContent = formatPercent(current);
  if (elements.gauge) {
    const angle = Math.min(100, Math.max(0, current)) * 3.6;
    elements.gauge.style.setProperty("--level-angle", `${angle}deg`);
    elements.gauge.setAttribute("aria-label", `Current tank level: ${formatPercent(current)}`);
  }

  // Vertical Liquid Cylinder Visualizer
  if (elements.tankLiquidFill) {
    elements.tankLiquidFill.style.height = `${Math.min(100, Math.max(0, current))}%`;
    elements.tankLiquidFill.classList.toggle("is-low-level", isLow);
  }

  // Freshness Beacon & Header Eyebrow
  if (elements.liveBeacon) {
    elements.liveBeacon.classList.toggle("is-stale", isStale);
    elements.liveBeacon.title = isStale ? "Historical telemetry (>24h stale)" : "Live telemetry stream active";
  }
  if (elements.eyebrowText) {
    elements.eyebrowText.textContent = isStale
      ? "AQUASENSE · HISTORICAL TELEMETRY (STALE)"
      : "AQUASENSE · TELEMETRY FIELD NODE";
  }

  // Stale Notification Banner
  if (elements.staleBanner) {
    elements.staleBanner.hidden = !isStale;
    if (isStale && elements.staleMessage && summary.latest_reading_timestamp) {
      elements.staleMessage.textContent = `Telemetry was recorded on ${formatTimestamp(summary.latest_reading_timestamp, { dateStyle: "medium", timeStyle: "short" })}. No live samples received in over 24 hours.`;
    }
  }

  // Status Chip & System Health Indicators
  if (elements.levelStatus) {
    elements.levelStatus.classList.remove("low", "stale");
    if (isLow) {
      elements.levelStatus.classList.add("low");
      elements.levelStatus.textContent = isStale ? "Critical Low (Historical)" : "Critical Low Level";
    } else if (isStale) {
      elements.levelStatus.classList.add("stale");
      elements.levelStatus.textContent = "Nominal (Historical)";
    } else {
      elements.levelStatus.textContent = "Optimal (Nominal)";
    }
  }

  if (elements.systemHealthDot) {
    elements.systemHealthDot.style.background = isLow ? "var(--red)" : (isStale ? "#f59e0b" : "var(--emerald)");
    elements.systemHealthDot.style.boxShadow = isLow
      ? "0 0 8px var(--red-glow)"
      : (isStale ? "0 0 8px rgba(245, 158, 11, 0.5)" : "0 0 8px var(--emerald-glow)");
  }
  if (elements.systemHealthText) {
    if (isLow) {
      elements.systemHealthText.textContent = isStale ? "Historical Low Violation" : "Low Threshold Alert";
      elements.systemHealthText.style.color = "#fb7185";
    } else if (isStale) {
      elements.systemHealthText.textContent = "Telemetry Stale (>24h)";
      elements.systemHealthText.style.color = "#fbbf24";
    } else {
      elements.systemHealthText.textContent = "Safe Capacity";
      elements.systemHealthText.style.color = "inherit";
    }
  }

  // Minimum & Maximum Cards
  setPercentStat(elements.minimum, summary.minimum_level);
  setPercentStat(elements.maximum, summary.maximum_level);

  // Last Updated Timestamp
  const readings = Array.isArray(summary.readings) ? summary.readings : [];
  const latestTimestamp = summary.latest_reading_timestamp || readings[readings.length - 1]?.timestamp;
  if (elements.updated) {
    elements.updated.textContent = latestTimestamp
      ? formatTimestamp(latestTimestamp, { dateStyle: "medium", timeStyle: "short" })
      : "Unavailable";
  }

  renderAlerts(isLow, current);
  renderEvents(Array.isArray(summary.historical_low_events) ? summary.historical_low_events : []);
  renderChart(readings);
}

// ==========================================================================
// SECURE DOM ALERT RENDERING (ZERO innerHTML)
// ==========================================================================

function renderAlerts(isLow, current) {
  if (!elements.activeCount || !elements.activeAlerts) return;
  elements.activeCount.textContent = isLow ? "1" : "0";
  elements.activeAlerts.replaceChildren();

  if (!isLow) {
    const empty = document.createElement("div");
    empty.className = "empty-state";

    const check = document.createElement("span");
    check.className = "empty-check";
    check.setAttribute("aria-hidden", "true");
    check.textContent = "✓";

    const textWrap = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = "All systems nominal";
    const desc = document.createElement("p");
    desc.textContent = "Tank capacity is comfortably above the 20% safety threshold.";
    textWrap.append(title, desc);

    empty.append(check, textWrap);
    elements.activeAlerts.append(empty);
    return;
  }

  const alert = document.createElement("div");
  alert.className = "alert-item";

  const symbol = document.createElement("span");
  symbol.className = "alert-symbol";
  symbol.setAttribute("aria-hidden", "true");
  symbol.textContent = "!";

  const copy = document.createElement("div");
  copy.className = "alert-item-copy";

  const title = document.createElement("strong");
  title.textContent = "Tank Level Below Safety Margin";

  const desc = document.createElement("p");
  desc.textContent = `Current volume is ${formatPercent(current)}, breaching the ${LOW_THRESHOLD}% critical reserve floor. Check intake valves and supply pump immediately.`;

  copy.append(title, desc);
  alert.append(symbol, copy);
  elements.activeAlerts.append(alert);
}

// ==========================================================================
// SECURE DOM EVENT RENDERING (ZERO innerHTML)
// ==========================================================================

function renderEvents(events) {
  if (!elements.eventCount || !elements.events) return;
  elements.eventCount.textContent = String(events.length);
  elements.events.replaceChildren();

  if (events.length === 0) {
    const empty = document.createElement("div");
    empty.className = "event-empty";
    empty.textContent = "No historical threshold violations logged in current cycle.";
    elements.events.append(empty);
    return;
  }

  events.slice().sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)).forEach((event) => {
    const row = document.createElement("div");
    row.className = "event-row";
    
    const marker = document.createElement("span");
    marker.className = "event-marker";
    marker.setAttribute("aria-hidden", "true");
    
    const copy = document.createElement("div");
    copy.className = "event-copy";
    const title = document.createElement("strong");
    title.textContent = "Low-Level Safety Event";
    const when = document.createElement("span");
    when.textContent = formatTimestamp(event.timestamp, { dateStyle: "medium", timeStyle: "short" });
    copy.append(title, when);

    const value = document.createElement("span");
    value.className = "event-value";
    value.textContent = formatPercent(Number(event.level)).replace("%", "");
    const unit = document.createElement("small");
    unit.textContent = "%";
    value.append(unit);

    row.append(marker, copy, value);
    elements.events.append(row);
  });
}

// ==========================================================================
// TIME-PROPORTIONAL SVG TELEMETRY CHART
// ==========================================================================

function renderChart(readings) {
  if (!elements.chartGrid) return;

  [elements.chartGrid, elements.chartThreshold, elements.chartArea,
    elements.chartLine, elements.chartPoints, elements.chartLabels]
    .forEach((group) => { if (group) group.replaceChildren(); });

  const chartWidth = 760;
  const chartHeight = 280;
  const left = 46;
  const right = 20;
  const top = 18;
  const bottom = 38;
  const plotWidth = chartWidth - left - right;
  const plotHeight = chartHeight - top - bottom;
  const yFor = (level) => top + ((100 - level) / 100) * plotHeight;

  // Grid lines & Y-axis labels
  [0, 20, 40, 60, 80, 100].forEach((tick) => {
    const y = yFor(tick);
    elements.chartGrid.append(svgElement("line", {
      x1: left, y1: y, x2: chartWidth - right, y2: y, class: "chart-grid-line",
    }));
    elements.chartLabels.append(svgElement("text", {
      x: left - 10, y: y + 3.5, "text-anchor": "end", class: "chart-y-label",
    }, `${tick}%`));
  });

  // Threshold Line at 20%
  const thresholdY = yFor(LOW_THRESHOLD);
  elements.chartThreshold.append(
    svgElement("line", { x1: left, y1: thresholdY, x2: chartWidth - right, y2: thresholdY, class: "chart-threshold-line" }),
    svgElement("text", { x: chartWidth - right - 4, y: thresholdY - 7, "text-anchor": "end", class: "chart-threshold-label" }, `${LOW_THRESHOLD}% Floor`),
  );

  if (!readings || readings.length === 0) {
    if (elements.chartEmpty) elements.chartEmpty.hidden = false;
    return;
  }
  if (elements.chartEmpty) elements.chartEmpty.hidden = true;

  const points = calculateChartPoints(readings, chartWidth, chartHeight, { left, right, top, bottom });

  const pathData = points.map((point, index) => `${index === 0 ? "M" : "L"}${point.x},${point.y}`).join(" ");
  const areaData = `${pathData} L${points[points.length - 1].x},${top + plotHeight} L${points[0].x},${top + plotHeight} Z`;

  // Defs & Gradient for Area Fill
  const defs = svgElement("defs");
  const gradient = svgElement("linearGradient", { id: "levelFillModern", x1: "0", y1: "0", x2: "0", y2: "1" });
  gradient.append(svgElement("stop", { offset: "0%", "stop-color": "#06b6d4", "stop-opacity": "0.38" }));
  gradient.append(svgElement("stop", { offset: "70%", "stop-color": "#0284c7", "stop-opacity": "0.10" }));
  gradient.append(svgElement("stop", { offset: "100%", "stop-color": "#0284c7", "stop-opacity": "0.01" }));
  defs.append(gradient);

  elements.chartArea.append(defs, svgElement("path", { d: areaData, fill: "url(#levelFillModern)" }));
  elements.chartLine.append(svgElement("path", { d: pathData, class: "chart-main-line" }));

  // Points and Interactive Tooltip Trigger
  points.forEach(({ x, y, reading, isUnderThreshold }) => {
    const point = svgElement("circle", {
      cx: x, cy: y, r: 5,
      class: isUnderThreshold ? "chart-point low-point" : "chart-point",
    });

    // Native tooltip fallback
    point.append(svgElement("title", {}, `${formatTimestamp(reading.timestamp, { dateStyle: "medium", timeStyle: "short" })}: ${formatPercent(Number(reading.level))}`));

    // Hover tooltip interaction
    point.addEventListener("mouseenter", () => {
      if (elements.chartTooltip && elements.chartWrap) {
        const wrapRect = elements.chartWrap.getBoundingClientRect();
        const svgRect = elements.chart.getBoundingClientRect();
        const scaleX = svgRect.width / chartWidth;
        const scaleY = svgRect.height / chartHeight;
        const pixelX = (x * scaleX) + (svgRect.left - wrapRect.left);
        const pixelY = (y * scaleY) + (svgRect.top - wrapRect.top);

        elements.chartTooltip.style.left = `${pixelX}px`;
        elements.chartTooltip.style.top = `${pixelY}px`;
        if (elements.tooltipTime) {
          elements.tooltipTime.textContent = formatTimestamp(reading.timestamp, { hour: "numeric", minute: "2-digit" });
        }
        if (elements.tooltipVal) {
          elements.tooltipVal.textContent = formatPercent(Number(reading.level));
        }
        elements.chartTooltip.hidden = false;
      }
    });

    point.addEventListener("mouseleave", () => {
      if (elements.chartTooltip) elements.chartTooltip.hidden = true;
    });

    elements.chartPoints.append(point);
  });

  // First and Last timestamps on X-Axis
  const first = readings[0]?.timestamp;
  const last = readings[readings.length - 1]?.timestamp;
  if (first && last) {
    elements.chartLabels.append(
      svgElement("text", { x: left, y: chartHeight - 10, "text-anchor": "start", class: "chart-x-label" }, formatTimestamp(first, { hour: "numeric", minute: "2-digit" })),
      svgElement("text", { x: chartWidth - right, y: chartHeight - 10, "text-anchor": "end", class: "chart-x-label" }, formatTimestamp(last, { hour: "numeric", minute: "2-digit" })),
    );
  }
}

// ==========================================================================
// SEPARATE DEVICE HARDWARE STATUS TELEMETRY
// ==========================================================================

async function getAuthToken(signal) {
  if (cachedAuthToken) return cachedAuthToken;
  try {
    const res = await fetch(`${API_BASE}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: "demo", password: "aqua123" }),
      signal,
    });
    if (res.ok) {
      const data = await res.json();
      if (data && typeof data.access_token === "string") {
        cachedAuthToken = data.access_token;
        try {
          sessionStorage.setItem("aquasense_token", cachedAuthToken);
        } catch (_) {}
        return cachedAuthToken;
      }
    }
  } catch (err) {
    if (err.name !== "AbortError") {
      console.warn("Could not acquire auth token for device status check:", err);
    }
  }
  return null;
}

async function updateDeviceStatus(signal) {
  if (!elements.deviceStatusTag) return;

  const token = await getAuthToken(signal);
  if (!token) {
    setDeviceStatusUI("unknown", "Auth Required");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/device/tank-001/status`, {
      headers: {
        "Authorization": `Bearer ${token}`,
        "Accept": "application/json",
      },
      cache: "no-store",
      signal,
    });

    if (res.status === 503) {
      // Backend reported device hardware is offline
      setDeviceStatusUI("offline", "Offline");
      return;
    }

    if (res.status === 401 || res.status === 403) {
      try {
        sessionStorage.removeItem("aquasense_token");
      } catch (_) {}
      cachedAuthToken = null;
      setDeviceStatusUI("unknown", "Auth Required");
      return;
    }

    if (!res.ok) {
      setDeviceStatusUI("unknown", "Unreachable");
      return;
    }

    const deviceData = await res.json();
    validateDeviceStatus(deviceData);

    if (!deviceData.online) {
      setDeviceStatusUI("offline", "Offline");
    } else if (deviceData.is_stale) {
      setDeviceStatusUI("stale", "Stale");
    } else {
      setDeviceStatusUI("online", "Online");
    }
  } catch (err) {
    if (err.name === "AbortError") return;
    // Network failure checking device status does NOT mean device is offline
    setDeviceStatusUI("unknown", "Unknown");
  }
}

// ==========================================================================
// ASYNCHRONOUS DASHBOARD LOADER WITH RACE PROTECTION & CACHE RETENTION
// ==========================================================================

async function loadDashboard() {
  if (activeDashboardController) {
    activeDashboardController.abort();
  }
  activeDashboardController = new AbortController();
  const currentSignal = activeDashboardController.signal;
  const timeoutId = window.setTimeout(() => activeDashboardController.abort(), 10000);

  if (elements.refresh) {
    elements.refresh.disabled = true;
    elements.refresh.classList.add("is-spinning");
  }
  if (elements.cachedRetry) elements.cachedRetry.disabled = true;
  if (!lastValidSummary && elements.loading) elements.loading.hidden = false;
  setConnection("loading", "API: Updating");

  try {
    const summaryPromise = fetch(`${API_BASE}/api/tank/summary`, {
      headers: { Accept: "application/json" },
      cache: "no-store",
      signal: currentSignal,
    });

    const devicePromise = updateDeviceStatus(currentSignal);

    const response = await summaryPromise;
    if (!response.ok) {
      throw new Error(`API returned ${response.status} ${response.statusText}`.trim());
    }

    const rawSummary = await response.json();
    const summary = validateTankSummary(rawSummary);

    lastValidSummary = summary;
    if (elements.cachedBanner) elements.cachedBanner.hidden = true;
    if (elements.error) elements.error.hidden = true;

    renderMetrics(summary);
    setConnection("connected", "API: Connected");

    await devicePromise;
  } catch (error) {
    if (error.name === "AbortError") return;
    console.error("AquaSense telemetry error:", error);
    setConnection("error", "API: Offline");

    if (lastValidSummary) {
      // Retain previous metrics on screen, display cached warning banner
      if (elements.cachedBanner) {
        elements.cachedBanner.hidden = false;
        if (elements.cachedMessage) {
          elements.cachedMessage.textContent = `Backend service unreachable (${error.message}). Retaining last verified telemetry.`;
        }
      }
      if (elements.error) elements.error.hidden = true;
    } else {
      // Initial load failure with no prior cache
      if (elements.errorMessage) {
        elements.errorMessage.textContent = `${error.message}. Verify that the AquaSense backend is running.`;
      }
      if (elements.error) elements.error.hidden = false;
      if (elements.cachedBanner) elements.cachedBanner.hidden = true;
    }
  } finally {
    window.clearTimeout(timeoutId);
    if (elements.loading) elements.loading.hidden = true;
    if (elements.grid) elements.grid.setAttribute("aria-busy", "false");
    if (elements.refresh) {
      elements.refresh.disabled = false;
      elements.refresh.classList.remove("is-spinning");
    }
    if (elements.cachedRetry) elements.cachedRetry.disabled = false;
  }
}

// ==========================================================================
// SCROLL EFFECTS & VISUAL INTERACTION
// ==========================================================================

function triggerRevealAnimations() {
  const revealItems = document.querySelectorAll(".reveal");
  revealItems.forEach((item) => item.classList.add("is-visible"));
}

function initializeScrollEffects() {
  const revealItems = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    const observer = new IntersectionObserver((entries, activeObserver) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          activeObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1, rootMargin: "0px 0px -20px 0px" });
    revealItems.forEach((item) => observer.observe(item));
  } else {
    revealItems.forEach((item) => item.classList.add("is-visible"));
  }

  const progress = document.querySelector("#scroll-progress");
  const topbar = document.querySelector("#topbar");
  let frameQueued = false;
  const updateScrollUI = () => {
    const scrollable = document.documentElement.scrollHeight - window.innerHeight;
    const percent = scrollable > 0 ? (window.scrollY / scrollable) * 100 : 0;
    if (progress) progress.style.width = `${Math.min(100, Math.max(0, percent))}%`;
    if (topbar) topbar.classList.toggle("is-scrolled", window.scrollY > 8);
    frameQueued = false;
  };
  window.addEventListener("scroll", () => {
    if (!frameQueued) {
      frameQueued = true;
      window.requestAnimationFrame(updateScrollUI);
    }
  }, { passive: true });
  window.addEventListener("resize", updateScrollUI, { passive: true });
  updateScrollUI();
}

// ==========================================================================
// EVENT LISTENERS & INITIALIZATION
// ==========================================================================

// Refresh & Retry controls
if (elements.refresh) elements.refresh.addEventListener("click", () => loadDashboard());
if (elements.retry) elements.retry.addEventListener("click", () => loadDashboard());
if (elements.cachedRetry) elements.cachedRetry.addEventListener("click", () => loadDashboard());

// Welcome Screen CTA & Dismissal
if (elements.enterDashboardBtn) {
  elements.enterDashboardBtn.addEventListener("click", dismissWelcomeScreen);
}
if (elements.replayIntroBtn) {
  elements.replayIntroBtn.addEventListener("click", showWelcomeScreen);
}

// Keyboard shortcut (Enter or Space to skip welcome)
window.addEventListener("keydown", (e) => {
  if (elements.welcomeScreen && !elements.welcomeScreen.hidden && !elements.welcomeScreen.classList.contains("is-leaving")) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      dismissWelcomeScreen();
    }
  }
});

// Theme Switcher
if (elements.themeToggleBtn) {
  elements.themeToggleBtn.addEventListener("click", toggleTheme);
}

// Periodic auto-refresh every 25 seconds for live telemetry
window.setInterval(() => {
  if (document.visibilityState === "visible") {
    loadDashboard();
  }
}, 25000);

// Initialize all features
initTheme();
initWelcomeParticles();
startWelcomeCountdown(3);
initializeScrollEffects();
loadDashboard();

// Expose utilities for testing environments
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    validateTankReading,
    validateTankSummary,
    validateDeviceStatus,
    calculateChartPoints,
    evaluateAlertThreshold,
    LOW_THRESHOLD,
  };
}

if (typeof window !== "undefined") {
  window.AquaSense = {
    validateTankReading,
    validateTankSummary,
    validateDeviceStatus,
    calculateChartPoints,
    evaluateAlertThreshold,
    loadDashboard,
    LOW_THRESHOLD,
  };
}
