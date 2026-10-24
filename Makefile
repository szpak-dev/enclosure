.PHONY: browser-build ci ci-browser-build ci-browser-build-check ci-browser-checks ci-browser-tests ci-python-checks ci-python-tests ci-python-tests-general ci-python-tests-health ci-python-tests-health-parallel ci-python-tests-health-process ci-python-tests-health-serial ci-python-tests-parallel ci-static-check ci-static-prepare ci-storybook-contract dev docs docs-check docs-generated docs-generated-check docs-linkcheck docs-links docs-lock docs-versioned format mcp renderer-install renderer-sync runtime-config runtime-down runtime-logs runtime-rollback runtime-up superuser

RENDERER_CACHE := $(CURDIR)/.dev/puppeteer
RUN := PATH="$(CURDIR)/node_modules/.bin:$(PATH)" PUPPETEER_CACHE_DIR="$(RENDERER_CACHE)" uv run
NPM := NPM_CONFIG_CACHE="$(CURDIR)/.dev/npm-cache" npm
NPX := NPM_CONFIG_CACHE="$(CURDIR)/.dev/npm-cache" PUPPETEER_CACHE_DIR="$(RENDERER_CACHE)" npx

dev:
	$(RUN) manage.py runserver

mcp:
	$(RUN) manage.py check
	$(RUN) uvicorn enclosure.core.asgi:application --app-dir src --host 127.0.0.1 --port 8000 --reload

renderer-sync:
	@mermaid_version="$$(uv run python -c 'from mermaiden import Application; application = Application.create(); print(application.mermaid_version); application.close()')"; \
	mermaid_cli_version="$$(uv run python -c 'from mermaiden import Application; application = Application.create(); print(application.mermaid_cli_version); application.close()')"; \
	PUPPETEER_SKIP_DOWNLOAD=true $(NPM) install --save-dev --save-exact \
		"mermaid@$$mermaid_version" "@mermaid-js/mermaid-cli@$$mermaid_cli_version"

renderer-install:
	@$(NPM) ci
	@$(NPX) puppeteer browsers install

browser-build:
	$(NPM) --prefix browser ci
	$(NPM) --prefix browser run typecheck
	$(NPM) --prefix browser run build

format:
	@uv run ruff format .
	@uv run ruff check --fix .
	@$(NPM) --prefix browser run format

ci:
	@$(MAKE) --jobs=2 ci-python-checks ci-browser-checks
	@$(MAKE) ci-static-prepare
	@$(MAKE) --jobs=2 ci-python-tests-parallel ci-browser-tests
	@$(MAKE) ci-python-tests-health-serial
	@$(MAKE) ci-python-tests-health-process
	@$(MAKE) ci-storybook-contract
	@$(MAKE) ci-browser-build-check
	@$(MAKE) docs-check

docs-generated:
	@PYTHONPATH=src $(RUN) --locked python scripts/generate_docs.py

docs-generated-check:
	@PYTHONPATH=src $(RUN) --locked python scripts/generate_docs.py --check

docs-links:
	@$(RUN) --isolated --no-project --python 3.14 python scripts/check_docs_links.py

docs-check: docs-generated-check docs-links
	@rm -rf docs/_build/html
	@PYTHONPATH=src $(RUN) --isolated --locked --with-requirements docs/requirements.lock sphinx-build -W --keep-going -E -a -b html docs docs/_build/html

docs: docs-generated
	@rm -rf docs/_build/html
	@PYTHONPATH=src $(RUN) --isolated --locked --with-requirements docs/requirements.lock sphinx-build -b html docs docs/_build/html

docs-linkcheck:
	@rm -rf docs/_build/linkcheck
	@PYTHONPATH=src $(RUN) --isolated --locked --with-requirements docs/requirements.lock sphinx-build -W --keep-going -E -a -b linkcheck docs docs/_build/linkcheck

docs-versioned:
	@$(RUN) --locked python scripts/build_versioned_docs.py

docs-lock:
	@uv pip compile --python-version 3.14 --universal --output-file docs/requirements.lock docs/requirements.in

ci-python-checks:
	@$(RUN) ruff format --check .
	@$(RUN) ruff check .
	@$(RUN) python manage.py check

ci-browser-checks:
	@$(NPM) --prefix browser run typecheck
	@$(NPM) --prefix browser run format:check

ci-python-tests:
	@$(MAKE) ci-python-tests-parallel
	@$(MAKE) ci-python-tests-health-serial
	@$(MAKE) ci-python-tests-health-process

ci-python-tests-parallel:
	@$(RUN) pytest -n 4 --dist worksteal -m "not health_serial"

ci-python-tests-general:
	@$(RUN) pytest -n 4 --dist worksteal -m "not health"

ci-python-tests-health:
	@$(MAKE) ci-python-tests-health-parallel
	@$(MAKE) ci-python-tests-health-serial
	@$(MAKE) ci-python-tests-health-process

ci-python-tests-health-parallel:
	@$(RUN) pytest -n 4 --dist worksteal -m "health and not health_serial"

ci-python-tests-health-serial:
	@$(RUN) pytest -m "health and health_serial and not health_process"

ci-python-tests-health-process:
	@$(RUN) pytest -m "health and health_process"

ci-browser-tests:
	@$(NPM) --prefix browser test
	@$(NPM) --prefix browser run storybook:test

ci-storybook-contract:
	@$(NPM) --prefix browser run storybook:build
	@$(NPM) --prefix browser run storybook:contract

ci-browser-build:
	@$(NPM) --prefix browser run build

ci-browser-build-check:
	@temporary="$$(mktemp -d)"; \
	trap 'rm -rf "$$temporary"' EXIT; \
	git diff --binary -- src/enclosure/browser/adapters/http/static/browser > "$$temporary/before.patch"; \
	$(MAKE) ci-browser-build; \
	git diff --binary -- src/enclosure/browser/adapters/http/static/browser > "$$temporary/after.patch"; \
	cmp "$$temporary/before.patch" "$$temporary/after.patch"

ci-static-prepare:
	@$(RUN) python manage.py collectstatic --noinput

ci-static-check:
	@git diff --exit-code -- src/enclosure/browser/adapters/http/static/browser

superuser:
	@$(RUN) manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); user, _ = User.objects.get_or_create(username='enclosure', defaults={'email': 'enclosure@localhost'}); user.email = 'enclosure@localhost'; user.is_staff = True; user.is_superuser = True; user.set_password('enclosure'); user.save(); print('Superuser enclosure is ready.')"

runtime-config:
	docker compose config --quiet

runtime-up:
	@set -eu; \
	image="$$(docker compose config --images | head -n 1)"; \
	repository="$${image%:*}"; \
	local_repository="$${repository#docker.io/}"; \
	local_current="$${local_repository}:$${image##*:}"; \
	local_previous="$${local_repository}:previous"; \
	previous="$${image%:*}:previous"; \
	current="$$(docker image inspect --format '{{.Id}}' "$$image" 2>/dev/null || true)"; \
	docker compose pull mcp; \
	pulled="$$(docker image inspect --format '{{.Id}}' "$$image")"; \
	if [ -n "$$current" ] && [ "$$current" != "$$pulled" ]; then docker image tag "$$current" "$$previous"; fi; \
	docker compose run --rm --no-deps --user root --entrypoint chown migrate -R 10001:10001 /var/cache/enclosure; \
	docker compose run --rm --no-deps migrate; \
	docker compose up --detach mcp; \
	stale="$$(docker image ls --format '{{.Repository}}:{{.Tag}} {{.ID}}' | awk -v current="$$local_current" -v previous="$$local_previous" -v repository="$$local_repository" '$$1 != current && $$1 != previous && (index($$1, repository ":") == 1 || $$1 == "enclosure:mcp") { print $$2 }' | sort -u)"; \
	if [ -n "$$stale" ]; then docker image rm $$stale; fi; \
	docker image prune --force

runtime-down:
	docker compose down

runtime-logs:
	docker compose logs --follow mcp

runtime-rollback:
	@set -eu; \
	image="$$(docker compose config --images | head -n 1)"; \
	previous="$${image%:*}:previous"; \
	docker image inspect "$$previous" >/dev/null; \
	ENCLOSURE_IMAGE="$$previous" docker compose run --pull never --rm --no-deps migrate; \
	ENCLOSURE_IMAGE="$$previous" docker compose up --pull never --detach --force-recreate mcp
