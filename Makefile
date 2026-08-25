dev:
	uv run manage.py runserver

mcp:
	uv run manage.py check
	uv run uvicorn enclosure.core.asgi:application --app-dir src --host 127.0.0.1 --port 8000 --reload

browser-build:
	npm --prefix browser ci
	npm --prefix browser run typecheck
	npm --prefix browser run build

superuser:
	@uv run manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); user, _ = User.objects.get_or_create(username='enclosure', defaults={'email': 'enclosure@localhost'}); user.email = 'enclosure@localhost'; user.is_staff = True; user.is_superuser = True; user.set_password('enclosure'); user.save(); print('Superuser enclosure is ready.')"

runtime-config:
	docker compose config --quiet

runtime-up:
	@set -eu; \
	image="$${ENCLOSURE_IMAGE:?Set ENCLOSURE_IMAGE in .env}"; \
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
