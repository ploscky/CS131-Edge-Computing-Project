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

app.listen(3000, "0.0.0.0", () => {
    console.log(`Server running on http://localhost:3000`);
});

//To test on another device run 
// ipconfig 
// and find IPv4 Address, then go to http://<IP_ADDRESS>:3000 in your browser

//when demoing
// get IP adress and make a qr code to join website
// if it doesnt work on school wifi, use a hotspot and make another qr code to join network first