@echo off
rem AFK: cut garments (SAM2) from 20 random samples, then Uniqlo-style product
rem shots (SDXL). Two phases = clean 8GB VRAM handoff. Detached/hidden launch.
cd /d "%~dp0..\.."
set LOG=pipeline\logs\afk-garments.out

echo === AFK GARMENTS START %DATE% %TIME% === >> "%LOG%"
echo [1/2] cut phase (GroundingDINO + SAM2, 20 samples)... >> "%LOG%"
python pipeline\scripts\afk_cut.py >> "%LOG%" 2>&1
echo [2/2] shot phase (SDXL product shots)... >> "%LOG%"
python pipeline\scripts\afk_shots.py >> "%LOG%" 2>&1
echo === AFK GARMENTS DONE %DATE% %TIME% === >> "%LOG%"
