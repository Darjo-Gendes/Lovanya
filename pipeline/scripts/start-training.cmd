@echo off
rem Detached QLoRA training run (see TRAINING.md).
cd /d "%~dp0..\.."
python pipeline\scripts\train_qlora.py --epochs 2 >> "pipeline\logs\training-run.out" 2>&1
