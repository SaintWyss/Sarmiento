.PHONY: init up down restart logs ps test check smoke backup restore

init:
	python3 ops/init_env.py

up:
	cd infra && docker compose --env-file .env up -d --build

down:
	cd infra && docker compose --env-file .env down

restart:
	cd infra && docker compose --env-file .env restart

logs:
	cd infra && docker compose --env-file .env logs -f --tail=200

ps:
	cd infra && docker compose --env-file .env ps

test:
	cd control-plane && python -m pytest -q

check:
	python -m compileall -q control-plane/src control-plane/migrations agent/sarmiento_agent.py ops/init_env.py
	bash -n agent/install-linux.sh agent/install-macos.sh viewer/install-linux.sh viewer/install-macos.sh viewer/sarmiento-open.sh viewer/sarmiento-workstation.sh viewer/tests/test-viewer.sh control-plane/entrypoint.sh ops/backup.sh ops/restore.sh ops/smoke.sh
	node --check front/app.js
	node --check front/sw.js
	bash viewer/tests/test-viewer.sh
	cd control-plane && python -m pytest -q

smoke:
	./ops/smoke.sh $${URL:-http://localhost}

backup:
	./ops/backup.sh

restore:
	./ops/restore.sh $${BACKUP:?set BACKUP=/path/to/archive.tar.gz}
