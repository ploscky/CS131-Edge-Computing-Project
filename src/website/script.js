async function loadDashboard() {
    try {
        const response = await fetch("/data");
        const data = await response.json();

        document.getElementById("totalCapacity").innerText = data.totalCapacity;
        document.getElementById("peopleInside").innerText = data.peopleInside;
        document.getElementById("waiting").innerText = data.waiting;
        document.getElementById("seated").innerText = data.seated;
        document.getElementById("waitTime").innerText = data.estimatedWaitTime;
        document.getElementById("busyStatus").innerText = data.busyStatus;

        const bestTime = `${data.bestTime.start} - ${data.bestTime.end} ${data.bestTime.time}`;
        document.getElementById("bestTime").innerText = bestTime;

        const tableContainer = document.getElementById("tables");
        tableContainer.innerHTML = "";

        data.tables.forEach(table => {
            const div = document.createElement("div");

            div.className = table.status === "occupied" ? "occupied" : "open";

            div.innerText = `Table ${table.id} - ${table.status}`;

            tableContainer.appendChild(div);
        });

        const status = data.busyStatus.toLowerCase();
        const el = document.getElementById("busyStatus");
        el.innerText = status;
        el.classList.remove("not-busy", "busy", "very-busy");
        el.classList.add(status.replace(" ", "-"));
    } catch (error) {
        console.error("Error loading dashboard", error);
    }
}

function updateDateTime() {
    const now = new Date();
    const date = now.toLocaleDateString("en-US", { month: "long", day: "numeric" });
    const time = now.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
    document.getElementById("date").innerText = date;
    document.getElementById("time").innerText = time;
}

loadDashboard();
updateDateTime();

setInterval(loadDashboard, 2000);
setInterval(updateDateTime, 3000);

// peak hours chart
const DAY_MAP = {
    Monday: 1, Tuesday: 2, Wednesday: 3,
    Thursday: 4, Friday: 5, Saturday: 6, // closed sundays (using "The Habit" hours as ref)
};

async function loadChart() {
    const chartSection = document.getElementById("chart-section");
    try {
        const config = await fetch("/chart-config").then(r => r.json());

        if (!config.baseUrl || !config.chartId) {
            chartSection.style.display = "none";
            return;
        }

        const sdk = new ChartsEmbedSDK({ baseUrl: config.baseUrl });

        const chart = sdk.createChart({
            chartId: config.chartId,
            height: "480px",
            theme: "light",
            autoRefresh: true,
            maxDataAge: 60,
        });

        await chart.render(document.getElementById("occupancy-chart"));

        const todayIndex = new Date().getDay();
        const adjustedIndex = todayIndex === 0 ? 6 : todayIndex; 
        const todayName = Object.keys(DAY_MAP).find(k => DAY_MAP[k] === adjustedIndex);

        if (todayName) {
            document.querySelectorAll(".day-btn").forEach(b => {
                b.classList.toggle("active", b.dataset.day === todayName);
            });
            await chart.setFilter({ $expr: { $eq: [{ $dayOfWeek: "$timestamp" }, DAY_MAP[todayName]] } });
        }

        document.querySelectorAll(".day-btn").forEach(btn => {
            btn.addEventListener("click", async () => {
                document.querySelectorAll(".day-btn").forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                // await chart.setFilter({ day_of_week: DAY_MAP[btn.dataset.day] });
                await chart.setFilter({ $expr: { $eq: [{ $dayOfWeek: "$timestamp" }, DAY_MAP[btn.dataset.day]] } });
            });
        });

    } catch (err) {
        // hide the chart if there's an error
        chartSection.style.display = "none";

        // push error to console log instead of UI
        console.error("[chart] failed to load:", err);
    }
}

loadChart();