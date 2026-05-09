async function loadDashboard() {
    try {
        const response = await fetch("/data");
        const data = await response.json();

        document.getElementById("inside").innerText = data.inside;
        document.getElementById("waiting").innerText = data.waiting;
        document.getElementById("seated").innerText = data.seated;

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