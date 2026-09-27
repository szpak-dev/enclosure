.PHONY: browser-build ci ci-browser-build ci-browser-checks ci-browser-tests ci-python-checks ci-python-tests ci-static-check ci-static-prepare dev format mcp runtime-config runtime-down runtime-logs runtime-rollback runtime-up superuser

dev:
	uv run manage.py runserver

mcp:
	uv run manage.py check
	uv run uvicorn enclosure.core.asgi:application --app-dir src --host 127.0.0.1 --port 8000 --reload

browser-build:
	npm --prefix browser ci
	npm --prefix browser run typecheck
	npm --prefix browser run build

format:
	@uv run ruff format .
	@uv run ruff check --fix .
	@npm --prefix browser run format

ci:
	@$(MAKE) --jobs=2 ci-python-checks ci-browser-checks
	@$(MAKE) ci-static-prepare
	@$(MAKE) --jobs=2 ci-python-tests ci-browser-tests
	@$(MAKE) ci-browser-build ci-static-check

ci-python-checks:
	@uv run ruff format --check .
	@uv run ruff check .
	@uv run python manage.py check

ci-browser-checks:
	@npm --prefix browser run typecheck
	@npm --prefix browser run format:check

ci-python-tests:
	@uv run pytest -n 4 --dist loadfile -k "not health"
	@uv run pytest -k health

ci-browser-tests:
	@npm --prefix browser test

ci-browser-build:
	@npm --prefix browser run build

ci-static-prepare:
	@uv run python manage.py collectstatic --noinput

ci-static-check:
	@git diff --exit-code -- src/enclosure/browser/adapters/http/static/browser

superuser:
	@uv run manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); user, _ = User.objects.get_or_create(username='enclosure', defaults={'email': 'enclosure@localhost'}); user.email = 'enclosure@localhost'; user.is_staff = True; user.is_superuser = True; user.set_password('enclosure'); user.save(); print('Superuser enclosure is ready.')"

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
