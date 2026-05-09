const path = require("path");
const express = require("express");
const fs = require("fs");

const app = express();
const PORT = 3000;

app.use(express.static(path.join(__dirname, "website")));

app.get("/data", (req, res) => {
    const data = fs.readFileSync(path.join(__dirname, "data.json"));
    res.json(JSON.parse(data));
});

app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});