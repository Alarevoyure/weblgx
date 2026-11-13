/** @weblgx-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { loadBundle } from "@web/core/assets";
import { Component, onWillStart, onWillUnmount, useEffect, useRef, useState } from "@weblgx/owl";
import { KeepLast } from "@web/core/utils/concurrency";

const MIDNIGHT = "#16213e";
const MIST = "#5c7ea8";

// Couleurs des enchaînements, par type de navigation.
const CONVERSION = "#10B981"; // Vers une action (/contactus)
const STANDARD = "#2563EB";   // Navigation standard (/factory, /weblgx, /bcm)
const RETURN = "#64748B";     // Retour depuis /contactus
const NEUTRAL = "#94a3b8";    // Autres transitions
const STANDARD_PAGES = ["/factory", "/weblgx", "/bcm"];

// Échelle de bleus de la marque : plus la part est grande, plus la barre est foncée.
const PALETTE = [
    [0.0, [179, 198, 226]],
    [0.5, [92, 126, 168]],
    [1.0, [22, 33, 62]],
];

function lerpColor(a, b, t) {
    return a + (b - a) * t;
}

function shareColor(share) {
    const t = Math.max(0, Math.min(1, share));
    let lower = PALETTE[0];
    let upper = PALETTE[PALETTE.length - 1];
    for (let i = 0; i < PALETTE.length - 1; i++) {
        if (t >= PALETTE[i][0] && t <= PALETTE[i + 1][0]) {
            lower = PALETTE[i];
            upper = PALETTE[i + 1];
            break;
        }
    }
    const span = (upper[0] - lower[0]) || 1;
    const f = (t - lower[0]) / span;
    const [r, g, b] = [0, 1, 2].map((i) => Math.round(lerpColor(lower[1][i], upper[1][i], f)));
    return `rgb(${r}, ${g}, ${b})`;
}

class WebsiteDashboard extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.user = useService("user");
        this.companyService = useService("company");
        this.keepLast = new KeepLast();
        this.lineRef = useRef("line");
        this.multiRef = useRef("multi");
        this.hoursRef = useRef("hours");
        this.landingsRef = useRef("landings");
        this.flowsRef = useRef("flows");
        this.pagesRef = useRef("pages");
        this.countriesRef = useRef("countries");
        this.charts = [];
        this.periods = [
            { days: 7, label: "7 jours" },
            { days: 30, label: "30 jours" },
            { days: 90, label: "90 jours" },
        ];
        this.state = useState({
            period: 30,
            loading: true,
            stats: null,
        });

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
        });
        onWillUnmount(() => this.destroyCharts());

        useEffect(
            () => {
                this.fetchData();
            },
            () => [this.state.period, this.companyService.activeCompanyIds[0]]
        );
        useEffect(
            () => {
                this.renderCharts();
                return () => this.destroyCharts();
            },
            () => [this.state.stats]
        );
    }

    get display() {
        return { controlPanel: {} };
    }

    get kpis() {
        const stats = this.state.stats;
        if (!stats) {
            return [];
        }
        const previous = stats.previous || {};
        return [
            ["Visiteurs", stats.visitors, previous.visitors, previous.visitors_delta],
            ["Pages vues", stats.page_views, previous.page_views, previous.page_views_delta],
            ["Visites", stats.sessions, previous.sessions, previous.sessions_delta],
            ["Durée moyenne", stats.avg_duration, previous.avg_duration, previous.avg_duration_delta],
            ["Pages par visite", stats.pages_per_session, previous.pages_per_session, previous.pages_per_session_delta],
        ].map(([label, value, before, delta]) => ({
            label,
            value,
            before,
            deltaText: this.formatDelta(delta),
        }));
    }

    get multiKpis() {
        const stats = this.state.stats;
        if (!stats || !stats.multi) {
            return [];
        }
        const multi = stats.multi;
        return [
            ["Visiteurs", multi.visitors],
            ["Pages vues", multi.page_views],
            ["Visites", multi.sessions],
            ["Durée moyenne", multi.avg_duration],
            ["Pages par visite", multi.pages_per_session],
        ].map(([label, value]) => ({ label, value }));
    }

    matchesPage(path, page) {
        return path === page || path.startsWith(page + "/");
    }

    flowColor(label) {
        const parts = label.split("→").map((part) => part.trim());
        const next = parts[1] || "";
        const prev = parts[0] || "";
        if (this.matchesPage(next, "/contactus")) {
            return CONVERSION;
        }
        if (this.matchesPage(prev, "/contactus")) {
            return RETURN;
        }
        if (STANDARD_PAGES.some((page) => this.matchesPage(next, page))) {
            return STANDARD;
        }
        return NEUTRAL;
    }

    formatDelta(delta) {
        if (delta === null || delta === undefined) {
            return "";
        }
        return (delta > 0 ? "+" : "") + delta + " %";
    }

    setPeriod(days) {
        if (this.state.period !== days) {
            this.state.period = days;
        }
    }

    async fetchData() {
        this.state.loading = true;
        const dashboardData = await this.keepLast.add(
            this.rpc("/website/fetch_dashboard_data", {
                days: this.state.period,
                context: this.user.context,
            })
        );
        this.state.stats = dashboardData.analytics || null;
        this.state.loading = false;
    }

    destroyCharts() {
        for (const chart of this.charts) {
            chart.destroy();
        }
        this.charts = [];
    }

    renderCharts() {
        this.destroyCharts();
        const stats = this.state.stats;
        if (!stats || typeof Chart === "undefined") {
            return;
        }
        if (this.lineRef.el) {
            this.charts.push(new Chart(this.lineRef.el, this.lineConfig(
                stats.series.labels,
                stats.series.visitors,
                stats.series.page_views
            )));
        }
        if (this.multiRef.el) {
            this.charts.push(new Chart(this.multiRef.el, this.lineConfig(
                stats.series.labels,
                stats.series.multi_visitors,
                stats.series.multi_page_views
            )));
        }
        if (this.hoursRef.el) {
            this.charts.push(new Chart(this.hoursRef.el, this.barConfig(
                stats.hours.map((_, hour) => hour + " h"),
                stats.hours,
                "Arrivées",
                false
            )));
        }
        if (this.landingsRef.el && stats.landings.length) {
            this.charts.push(new Chart(this.landingsRef.el, this.barConfig(
                stats.landings.map((row) => row.label),
                stats.landings.map((row) => row.visits),
                "Visites"
            )));
        }
        if (this.flowsRef.el && stats.flows.length) {
            this.charts.push(new Chart(this.flowsRef.el, this.barConfig(
                stats.flows.map((row) => row.label),
                stats.flows.map((row) => row.visits),
                "Enchaînements",
                true,
                stats.flows.map((row) => this.flowColor(row.label))
            )));
        }
        if (this.pagesRef.el && stats.pages.length) {
            this.charts.push(new Chart(this.pagesRef.el, this.barConfig(
                stats.pages.map((row) => row.label),
                stats.pages.map((row) => row.views),
                "Pages vues"
            )));
        }
        if (this.countriesRef.el && stats.countries.length) {
            this.charts.push(new Chart(this.countriesRef.el, this.barConfig(
                stats.countries.map((row) => row.label),
                stats.countries.map((row) => row.visitors),
                "Visiteurs"
            )));
        }
    }

    lineConfig(labels, visitors, pageViews) {
        return {
            type: "line",
            data: {
                labels,
                datasets: [
                    {
                        label: "Visiteurs",
                        data: visitors,
                        borderColor: MIDNIGHT,
                        backgroundColor: "rgba(22, 33, 62, 0.12)",
                        fill: true,
                        tension: 0.25,
                        borderWidth: 2,
                        pointRadius: 2,
                    },
                    {
                        label: "Pages vues",
                        data: pageViews,
                        borderColor: MIST,
                        backgroundColor: "rgba(92, 126, 168, 0.08)",
                        fill: false,
                        tension: 0.25,
                        borderWidth: 2,
                        pointRadius: 2,
                    },
                ],
            },
            options: this.chartOptions(),
        };
    }

    barConfig(labels, data, legend, horizontal = true, colors = null) {
        const max = Math.max(1, ...data.filter((value) => value > 0));
        const backgroundColor = colors || data.map((value) => shareColor(value / max));
        return {
            type: "bar",
            data: {
                labels,
                datasets: [{
                    label: legend,
                    data,
                    backgroundColor,
                    borderRadius: 4,
                    maxBarThickness: horizontal ? 22 : 18,
                }],
            },
            options: this.chartOptions(horizontal ? { indexAxis: "y" } : {}),
        };
    }

    chartOptions(extra = {}) {
        const horizontal = extra.indexAxis === "y";
        return {
            responsive: true,
            maintainAspectRatio: false,
            ...extra,
            plugins: {
                legend: {
                    position: "bottom",
                    labels: { boxWidth: 12, color: "#3c4456" },
                },
            },
            scales: {
                x: {
                    beginAtZero: horizontal,
                    ticks: { precision: 0, color: "#5c6578" },
                    grid: { display: horizontal },
                },
                y: {
                    beginAtZero: !horizontal,
                    ticks: { precision: 0, color: "#5c6578" },
                    grid: { display: !horizontal },
                },
            },
        };
    }
}

WebsiteDashboard.template = "website.WebsiteDashboardMain";
WebsiteDashboard.components = { Layout };

registry.category("actions").add("backend_dashboard", WebsiteDashboard);
