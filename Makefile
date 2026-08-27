.PHONY: install run test health

install:
	docker compose build

run:
	docker compose up

test:
	docker compose -f docker-compose.test.yml up --build

health:
	./scripts/healthcheck.sh
