const path = require("path");
const express = require("express");
const fs = require("fs");

const app = express();
const PORT = process.env.PORT || 3000;

const MONGO_URI = process.env.MONGO_URI;
const MONGO_DB_NAME = process.env.MONGO_DB_NAME;
const LOCATION_ID = process.env.LOCATION_ID;

let db = null;
 
async function connectMongo() {
    if (!MONGO_URI) {
        console.warn("[server] MONGO_URI not set, /api/wait-history unavailable");
        return;
    }
    try {
        const client = new MongoClient(MONGO_URI, { serverSelectionTimeoutMS: 5000 });
        await client.connect();
        db = client.db(MONGO_DB_NAME);
        console.log("[server] Connected to MongoDB Atlas");
    } catch (err) {
        console.error("[server] MongoDB connection failed:", err.message);
    }
}

app.use(express.static(path.join(__dirname, "website")));

app.get("/data", (req, res) => {
    const data = fs.readFileSync(path.join(__dirname, "data.json"));
    res.json(JSON.parse(data));
});

app.listen(3000, "0.0.0.0", () => {
    console.log(`Server running on http://localhost:3000`);
});

connectMongo().then(() => {
    app.listen(PORT, () => {
        console.log(`[server] listening on http://localhost:${PORT}`);
    });
});

//To test on another device run 
// ipconfig 
// and find IPv4 Address, then go to http://<IP_ADDRESS>:3000 in your browser

//when demoing
// get IP adress and make a qr code to join website
// if it doesnt work on school wifi, use a hotspot and make another qr code to join network first