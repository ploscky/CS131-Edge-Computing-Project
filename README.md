# CS131-Edge-Computing-Project
# Campus Dining Capacity Tracker
 > Real-time occupancy monitoring for on-campus dining
 
Contributors: [Isaac Ja](https://github.com/IsaacJa75), [Caleb Mak](https://github.com/cmakkkk), [Nada Salib](https://github.com/nadasalib), [Andres Solorio](https://github.com/Andres-55), [Temuulen Tserenchimed](https://github.com/PlatsXD), [Selina Wu](https://github.com/ploscky)

---

## Overview
On-campus dining venues like The Barn and Coffee Bean currently offer no way to check seat availability before arriving. Students and faculty have no visibility into how busy a restaurant is.

This project brings real-time capacity tracking to campus dining, similar to how UCR already monitors parking lot availability. It monitors entrances, table occupancy, and wait queues using overhead cameras, then sends that data to a live web dashboard.

## Features
- **Live occupancy** — Tracks arrivals, departures, and current headcount in real time.
- **Table-level tracking** — Identifies which tables are occupied vs. open.
- **Wait time estimates** — Notifies waiting customers via web dashboard.
- **Peak time analytics** — Aggregates historical data to identify busy periods.
- **Public dashboard** - Web interface showing current and predicted occupancy.

## Task Distribution
### Edge Layer

We have two edge devices in the edge layer. A camera keeps track of the people entering and leaving the restaurant. The corresponding edge device (Jetson Nano) uses a simple counter that increments when a person enters and decrements when a person leaves. Another camera checks how many seats and booths in the restaurant are open; the Nano will be trained to detect and differentiate people and seats. This determines when somebody is occupying a seat. The two devices communicate with one another to keep track of how many people are waiting for a table inside the restaurant (people inside - people seated). Another counter is incremented and decremented based on the number of open seats. Together, the edge devices manage the state of table occupancy.

### Fog Layer

In the fog layer, we implement time limits to different areas within the restaurant to calculate an estimated waiting time. Each area has its own time limit. For example, booths have a 2 hour waiting time and bars have a 1.5 hour waiting time. This helps keep track of every table and aggregates the data captured by the edge devices. A laptop acts as the fog computing device to do this work.

### Cloud Layer

In the cloud, we keep track of how many seats are open and the amount of people entering and leaving over a long period of time. This data is used and analyzed to compute the peak times of the restaurant. The results of this analysis are displayed on a website, helping inform people of the restaurant’s traffic and expected occupancy at any given time.

## System Design
<img src="diagrams/system_design_diagram.jpg" alt="Description" width="800">

## Workload Distribution
<img src="diagrams/workload_distribution_diagram.jpg" alt="Description" width="800">

## Website Draft
<img width="1276" height="1018" alt="image" src="https://github.com/user-attachments/assets/2b155d15-16ef-48ed-8b4d-876e72e26a5f" />

## Tool Inventory
| Technology | Purpose |
|---|---|
| 2 Jetson Nanos | for analyzing video data, one for number of people in the building, the other for the number of people seated. |
| 2 cameras | to capture video feed. One is positioned at the entrance/exit to capture people entering and exiting. One is positioned above the room to capture the tables and people. |
| Laptop | to calculate live wait times and aggregate data. It sends this information to the cloud for long-term storage and calculation. |

## Acknowledgements
This project is developed as part of UCR's CS131 Edge Computing course taught by Professor Neftali.
