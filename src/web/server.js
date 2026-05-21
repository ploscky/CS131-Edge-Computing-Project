const path = require("path");
const express = require("express");
const fs = require("fs");

const app = express();
const PORT = process.env.PORT || 3000;
const PUBLIC_DIR = path.join(__dirname, "public");
const DASHBOARD_DATA_FILE = path.join(__dirname, "..", "data", "dashboard.json");

app.use(express.static(PUBLIC_DIR));

app.get("/data", (req, res) => {
    try {
        const data = fs.readFileSync(DASHBOARD_DATA_FILE, "utf8");
        res.json(JSON.parse(data));
    } catch (err) {
        console.error("[server] Could not read dashboard data:", err.message);
        res.status(500).json({ error: "Dashboard data unavailable" });
    }
});

app.listen(PORT, "0.0.0.0", () => {
    console.log(`[server] listening on http://localhost:${PORT}`);
});

// To test on another device run:
// ipconfig 
// and find IPv4 Address, then go to http://<IP_ADDRESS>:3000 in your browser

// When demoing:
// get IP address and make a QR code to join website
// if it doesn't work on school wifi, use a hotspot and make another QR code to join network first
