exe:
	pyinstaller --onefile --paths=./src --distpath=./out --noconfirm --clean --icon=./favicon.ico --add-data "./favicon.ico;." --name="WLAN Monitor" src/wlan/main.py

reinstall:
	pip install -e . --force-reinstall --no-deps

start:
	python -m src.wlan.router.client

main:
	python -m src.wlan.main