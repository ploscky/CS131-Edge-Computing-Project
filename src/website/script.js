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

    const options = {
        month: "long",
        day: "numeric"
    };

    const date = now.toLocaleDateString("en-US", options);

    const time = now.toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit"
    });

    document.getElementById("date").innerText = date;
    document.getElementById("time").innerText = time;
}

loadDashboard();
updateDateTime();

setInterval(loadDashboard, 2000);
setInterval(updateDateTime, 3000);