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
	docker compose pull
	docker compose up --detach

runtime-down:
	docker compose down

runtime-logs:
	docker compose logs --follow mcp
