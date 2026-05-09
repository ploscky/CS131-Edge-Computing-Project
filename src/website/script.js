async function loadDashboard() {
    try {
        const response = await fetch("/data");
        const data = await response.json();

        document.getElementById("totalCapacity").innerText = data.totalCapacity;
        document.getElementById("peopleInside").innerText = data.peopleInside;
        document.getElementById("waiting").innerText = data.waiting;
        document.getElementById("seated").innerText = data.seated;
        document.getElementById("waitTime").innerText = data.estimatedWaitTime;

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

    } catch (error) {
        console.error("Error loading dashboard", error);
    }
}

loadDashboard();

setInterval(loadDashboard, 2000);