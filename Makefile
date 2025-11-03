exe:
	pyinstaller --onefile --paths=./src --distpath=./out src/wlan/main.py

reinstall:
	pip install -e . --force-reinstall --no-deps

start:
	python -m src.wlan.router.client

main:
	python -m src.wlan.main