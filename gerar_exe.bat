@echo off
pip install pyinstaller
rmdir /s /q build
rmdir /s /q dist
del /q SysmartFiscalHub.spec
pyinstaller --noconfirm --clean --windowed --onefile --name SysmartFiscalHub main.py
pause
