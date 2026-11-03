"use strict";

document.documentElement.classList.add("js-ready");

// Same-origin when served by FastAPI; retains support for the standalone dev server.
const API_BASE = window.AQUASENSE_API_BASE
  || (window.location.port === "5500" ? "http://127.0.0.1:8000" : window.location.origin);
const LOW_THRESHOLD = 20;
const SVG_NS = "http://www.w3.org/2000/svg";

const elements = {
  loading: document.querySelector("#loading-state"),
  error: document.querySelector("#error-state"),
  errorMessage: document.querySelector("#error-message"),
  grid: document.querySelector("#metric-grid"),
  refresh: document.querySelector("#refresh-button"),
  retry: document.querySelector("#retry-button"),
  connection: document.querySelector("#connection-status"),
  connectionLabel: document.querySelector("#connection-label"),
  gauge: document.querySelector("#level-gauge"),
  current: document.querySelector("#current-level"),
  currentCaption: document.querySelector("#current-caption"),
  levelStatus: document.querySelector("#level-status"),
  minimum: document.querySelector("#minimum-level"),
  maximum: document.querySelector("#maximum-level"),
  updated: document.querySelector("#last-updated"),
  activeAlerts: document.querySelector("#active-alerts"),
  activeCount: document.querySelector("#active-count"),
  events: document.querySelector("#historical-events"),
  eventCount: document.querySelector("#event-count"),
  chart: document.querySelector("#history-chart"),
  chartGrid: document.querySelector("#chart-grid"),
  chartThreshold: document.querySelector("#chart-threshold"),
  chartArea: document.querySelector("#chart-area"),
  chartLine: document.querySelector("#chart-line"),
  chartPoints: document.querySelector("#chart-points"),
  chartLabels: document.querySelector("#chart-labels"),
  chartEmpty: document.querySelector("#chart-empty"),
};

function setConnection(state, label) {
  elements.connection.classList.toggle("is-loading", state === "loading");
  elements.connection.classList.toggle("is-error", state === "error");
  elements.connectionLabel.textContent = label;
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
  elements.current.textContent = formatPercent(current);
  elements.currentCaption.textContent = formatPercent(current);
  setPercentStat(elements.minimum, summary.minimum_level);
  setPercentStat(elements.maximum, summary.maximum_level);
  elements.gauge.style.setProperty("--level-angle", `${Math.min(100, Math.max(0, current)) * 3.6}deg`);
  elements.gauge.setAttribute("aria-label", `Current tank level: ${formatPercent(current)}`);
  const isLow = Boolean(summary.active_alert);
  elements.levelStatus.textContent = isLow ? "Low level" : "Normal";
  elements.levelStatus.classList.toggle("low", isLow);

  const readings = Array.isArray(summary.readings) ? summary.readings : [];
  const latest = readings[readings.length - 1];
  elements.updated.textContent = latest?.timestamp
    ? formatTimestamp(latest.timestamp, { dateStyle: "medium", timeStyle: "short" })
    : "Unavailable";
  renderAlerts(isLow, current);
  renderEvents(Array.isArray(summary.historical_low_events) ? summary.historical_low_events : []);
  renderChart(readings);
}

function renderAlerts(isLow, current) {
  elements.activeCount.textContent = isLow ? "1" : "0";
  elements.activeAlerts.replaceChildren();
  if (!isLow) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.innerHTML = '<span class="empty-check" aria-hidden="true">✓</span><div><strong>All clear</strong><p>No active tank alerts right now.</p></div>';
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
  const title = document.createElement("strong");
  title.textContent = "Tank level below threshold";
  const body = document.createElement("p");
  body.textContent = `Current level is ${formatPercent(current)}, below the ${LOW_THRESHOLD}% safety threshold.`;
  copy.append(title, body);
  alert.append(symbol, copy);
  elements.activeAlerts.append(alert);
}

function renderEvents(events) {
  elements.eventCount.textContent = String(events.length);
  elements.events.replaceChildren();
  if (events.length === 0) {
    const empty = document.createElement("div");
    empty.className = "event-empty";
    empty.textContent = "No historical low-level events.";
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
    title.textContent = "Low-level reading";
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
  [elements.chartGrid, elements.chartThreshold, elements.chartArea,
    elements.chartLine, elements.chartPoints, elements.chartLabels]
    .forEach((group) => group.replaceChildren());

  const chartWidth = 760;
  const chartHeight = 280;
  const left = 43;
  const right = 18;
  const top = 15;
  const bottom = 36;
  const plotWidth = chartWidth - left - right;
  const plotHeight = chartHeight - top - bottom;
  const yFor = (level) => top + ((100 - level) / 100) * plotHeight;

  [0, 20, 40, 60, 80, 100].forEach((tick) => {
    const y = yFor(tick);
    elements.chartGrid.append(svgElement("line", {
      x1: left, y1: y, x2: chartWidth - right, y2: y, class: "chart-grid-line",
    }));
    elements.chartLabels.append(svgElement("text", {
      x: left - 10, y: y + 3, "text-anchor": "end", class: "chart-y-label",
    }, String(tick)));
  });

  const thresholdY = yFor(LOW_THRESHOLD);
  elements.chartThreshold.append(
    svgElement("line", { x1: left, y1: thresholdY, x2: chartWidth - right, y2: thresholdY, class: "chart-threshold-line" }),
    svgElement("text", { x: chartWidth - right - 2, y: thresholdY - 6, "text-anchor": "end", class: "chart-threshold-label" }, `${LOW_THRESHOLD}% threshold`),
  );

  if (readings.length === 0) {
    elements.chartEmpty.hidden = false;
    return;
  }
  elements.chartEmpty.hidden = true;
  const points = readings.map((reading, index) => ({
    x: readings.length === 1 ? left + plotWidth / 2 : left + (index / (readings.length - 1)) * plotWidth,
    y: yFor(Number(reading.level)),
    reading,
  }));
  const pathData = points.map((point, index) => `${index === 0 ? "M" : "L"}${point.x},${point.y}`).join(" ");
  const areaData = `${pathData} L${points[points.length - 1].x},${top + plotHeight} L${points[0].x},${top + plotHeight} Z`;
  const defs = svgElement("defs");
  const gradient = svgElement("linearGradient", { id: "levelFill", x1: "0", y1: "0", x2: "0", y2: "1" });
  gradient.append(svgElement("stop", { offset: "0%", "stop-color": "#42b8ac", "stop-opacity": ".22" }));
  gradient.append(svgElement("stop", { offset: "100%", "stop-color": "#42b8ac", "stop-opacity": ".01" }));
  defs.append(gradient);
  elements.chartArea.append(defs, svgElement("path", { d: areaData, class: "chart-area-path" }));
  elements.chartLine.append(svgElement("path", { d: pathData, class: "chart-main-line" }));

  points.forEach(({ x, y, reading }) => {
    const point = svgElement("circle", {
      cx: x, cy: y, r: 4.5,
      class: Number(reading.level) < LOW_THRESHOLD ? "chart-point low-point" : "chart-point",
    });
    point.append(svgElement("title", {}, `${formatTimestamp(reading.timestamp, { dateStyle: "medium", timeStyle: "short" })}: ${formatPercent(Number(reading.level))}`));
    elements.chartPoints.append(point);
  });

  const first = readings[0]?.timestamp;
  const last = readings[readings.length - 1]?.timestamp;
  elements.chartLabels.append(
    svgElement("text", { x: left, y: chartHeight - 9, "text-anchor": "start", class: "chart-x-label" }, formatTimestamp(first, { hour: "numeric", minute: "2-digit" })),
    svgElement("text", { x: chartWidth - right, y: chartHeight - 9, "text-anchor": "end", class: "chart-x-label" }, formatTimestamp(last, { hour: "numeric", minute: "2-digit" })),
  );
}

async function loadDashboard() {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), 10000);
  elements.loading.hidden = false;
  elements.error.hidden = true;
  elements.grid.setAttribute("aria-busy", "true");
  elements.refresh.disabled = true;
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
    elements.errorMessage.textContent = `${message} Make sure the backend is running and this page uses the correct API address.`;
    elements.error.hidden = false;
    setConnection("error", "API unavailable");
  } finally {
    window.clearTimeout(timeoutId);
    elements.loading.hidden = true;
    elements.grid.setAttribute("aria-busy", "false");
    elements.refresh.disabled = false;
  }
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
    }, { threshold: 0.12, rootMargin: "0px 0px -24px 0px" });
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
    progress.style.width = `${Math.min(100, Math.max(0, percent))}%`;
    topbar.classList.toggle("is-scrolled", window.scrollY > 8);
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

elements.refresh.addEventListener("click", loadDashboard);
elements.retry.addEventListener("click", loadDashboard);
initializeScrollEffects();
loadDashboard();
