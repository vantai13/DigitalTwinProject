#!/bin/bash

# Kích hoạt môi trường Python
source venv/bin/activate

# Chạy Flask Backend
python backend/app.py &

# Chạy Mininet Simulation
deactivate
sudo python3 mininet_twin/main.py &

# Chạy VueJS Frontend
cd frontend
npm run dev
