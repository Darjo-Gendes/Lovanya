@echo off
rem AFK pipeline: train on rebalanced gold, then auto-benchmark the new adapter.
rem Launched detached (hidden) so it survives the session closing.
cd /d "%~dp0..\.."
set LOG=pipeline\logs\afk-run.out

echo === AFK RUN START %DATE% %TIME% === >> "%LOG%"

echo [1/4] training (1 epoch on rebalanced gold)... >> "%LOG%"
python pipeline\scripts\train_qlora.py --epochs 1 >> "%LOG%" 2>&1

echo [2/4] eval on 7-sample set (new adapter via ADAPTER=auto)... >> "%LOG%"
python pipeline\scripts\eval_samples.py --out pipeline\EVAL-REPORT-rebalanced.md >> "%LOG%" 2>&1

echo [3/4] outlier discrimination check... >> "%LOG%"
python pipeline\scripts\check_outliers.py >> pipeline\logs\outliers-rebalanced.txt 2>> "%LOG%"

echo [4/4] benchmark vs rebalanced gold... >> "%LOG%"
python pipeline\scripts\benchmark.py --results pipeline\EVAL-REPORT-rebalanced.jsonl --out pipeline\BENCHMARK-rebalanced.md >> "%LOG%" 2>&1

echo === AFK RUN DONE %DATE% %TIME% === >> "%LOG%"
