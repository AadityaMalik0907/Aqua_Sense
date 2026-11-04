"use strict";

document.documentElement.classList.add("js-ready");

// API configuration: same-origin when served by FastAPI, or fallback to dev port 8000
const API_BASE = window.AQUASENSE_API_BASE
  || (window.location.protocol === "file:" || window.location.port === "5500" ? "http://127.0.0.1:8000" : window.location.origin);
const LOW_THRESHOLD = 20;
const SVG_NS = "http://www.w3.org/2000/svg";

const elements = {
  // Banners & State
  loading: document.querySelector("#loading-state"),
  error: document.querySelector("#error-state"),
  errorMessage: document.querySelector("#error-message"),
  grid: document.querySelector("#metric-grid"),
  refresh: document.querySelector("#refresh-button"),
  retry: document.querySelector("#retry-button"),
  connection: document.querySelector("#connection-status"),
  connectionLabel: document.querySelector("#connection-label"),
  
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

  // Inject keyframe if not present
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
// CONNECTION & RENDERING LOGIC
// ==========================================================================

function setConnection(state, label) {
  if (!elements.connection) return;
  elements.connection.classList.toggle("is-loading", state === "loading");
  elements.connection.classList.toggle("is-error", state === "error");
  if (elements.connectionLabel) elements.connectionLabel.textContent = label;
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

function renderMetrics(summary) {
  const current = Number(summary.current_level);
  const isLow = Boolean(summary.active_alert);

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

  // Status Chip & Health Indicators
  if (elements.levelStatus) {
    elements.levelStatus.textContent = isLow ? "Critical Low Level" : "Optimal (Nominal)";
    elements.levelStatus.classList.toggle("low", isLow);
  }

  if (elements.systemHealthDot) {
    elements.systemHealthDot.style.background = isLow ? "var(--red)" : "var(--emerald)";
    elements.systemHealthDot.style.boxShadow = isLow ? "0 0 8px var(--red-glow)" : "0 0 8px var(--emerald-glow)";
  }
  if (elements.systemHealthText) {
    elements.systemHealthText.textContent = isLow ? "Low Threshold Alert" : "Safe Capacity";
    elements.systemHealthText.style.color = isLow ? "#fb7185" : "inherit";
  }

  // Minimum & Maximum Cards
  setPercentStat(elements.minimum, summary.minimum_level);
  setPercentStat(elements.maximum, summary.maximum_level);

  // Last Updated Timestamp
  const readings = Array.isArray(summary.readings) ? summary.readings : [];
  const latest = readings[readings.length - 1];
  if (elements.updated) {
    elements.updated.textContent = latest?.timestamp
      ? formatTimestamp(latest.timestamp, { dateStyle: "medium", timeStyle: "short" })
      : "Unavailable";
  }

  renderAlerts(isLow, current);
  renderEvents(Array.isArray(summary.historical_low_events) ? summary.historical_low_events : []);
  renderChart(readings);
}

function renderAlerts(isLow, current) {
  if (!elements.activeCount || !elements.activeAlerts) return;
  elements.activeCount.textContent = isLow ? "1" : "0";
  elements.activeAlerts.replaceChildren();

  if (!isLow) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.innerHTML = `
      <span class="empty-check" aria-hidden="true">✓</span>
      <div>
        <strong>All systems nominal</strong>
        <p>Tank capacity is comfortably above the 20% safety threshold.</p>
      </div>
    `;
    elements.activeAlerts.append(empty);
    return;
  }

  const alert = document.createElement("div");
  alert.className = "alert-item";
  alert.innerHTML = `
    <span class="alert-symbol" aria-hidden="true">!</span>
    <div class="alert-item-copy">
      <strong>Tank Level Below Safety Margin</strong>
      <p>Current volume is ${formatPercent(current)}, breaching the ${LOW_THRESHOLD}% critical reserve floor. Check intake valves and supply pump immediately.</p>
    </div>
  `;
  elements.activeAlerts.append(alert);
}

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

  if (readings.length === 0) {
    if (elements.chartEmpty) elements.chartEmpty.hidden = false;
    return;
  }
  if (elements.chartEmpty) elements.chartEmpty.hidden = true;

  const points = readings.map((reading, index) => ({
    x: readings.length === 1 ? left + plotWidth / 2 : left + (index / (readings.length - 1)) * plotWidth,
    y: yFor(Number(reading.level)),
    reading,
  }));

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
  points.forEach(({ x, y, reading }) => {
    const isUnderThreshold = Number(reading.level) < LOW_THRESHOLD;
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

async function loadDashboard() {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), 10000);

  if (elements.loading) elements.loading.hidden = false;
  if (elements.error) elements.error.hidden = true;
  if (elements.grid) elements.grid.setAttribute("aria-busy", "true");
  if (elements.refresh) {
    elements.refresh.disabled = true;
    elements.refresh.classList.add("is-spinning");
  }
  setConnection("loading", "Updating");

  try {
    const response = await fetch(`${API_BASE}/api/tank/summary`, {
      headers: { Accept: "application/json" },
      cache: "no-store",
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`API returned ${response.status} ${response.statusText}`.trim());
    }

    const summary = await response.json();
    if (!Number.isFinite(Number(summary.current_level))
      || !Number.isFinite(Number(summary.minimum_level))
      || !Number.isFinite(Number(summary.maximum_level))
      || !Array.isArray(summary.readings)) {
      throw new Error("The API response is missing tank summary fields.");
    }

    renderMetrics(summary);
    setConnection("connected", "Connected");
  } catch (error) {
    const message = error.name === "AbortError"
      ? "The request timed out after 10 seconds."
      : error.message;
    console.error("AquaSense dashboard could not load tank data:", error);
    if (elements.errorMessage) {
      elements.errorMessage.textContent = `${message} Verify that the backend is running and this page connects to the correct API endpoint.`;
    }
    if (elements.error) elements.error.hidden = false;
    setConnection("error", "API unavailable");
  } finally {
    window.clearTimeout(timeoutId);
    if (elements.loading) elements.loading.hidden = true;
    if (elements.grid) elements.grid.setAttribute("aria-busy", "false");
    if (elements.refresh) {
      elements.refresh.disabled = false;
      elements.refresh.classList.remove("is-spinning");
    }
  }
}

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

// Refresh & Retry
if (elements.refresh) elements.refresh.addEventListener("click", loadDashboard);
if (elements.retry) elements.retry.addEventListener("click", loadDashboard);

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
