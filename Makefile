exe:
	pyinstaller --onefile --paths=./src --distpath=./out --noconfirm --clean --icon=./favicon.ico --add-data "./favicon.ico;." --name="WLAN Monitor" src/wlan/main.py

ri:
	pip install -e . --force-reinstall --no-deps

main:
	python -m src.wlan.main

router:
	python -m src.wlan.router.client

extender:
	python -m src.wlan.extender.client