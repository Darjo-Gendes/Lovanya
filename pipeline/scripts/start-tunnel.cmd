@echo off
rem Detached Cloudflare quick tunnel for the Lovanya test bench.
rem URL appears in pipeline\logs\tunnel.out (search for trycloudflare.com).
cd /d "%~dp0..\.."
"C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://localhost:8000 > "pipeline\logs\tunnel.out" 2>&1
