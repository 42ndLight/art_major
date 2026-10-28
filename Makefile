.PHONY: run test migrate makemigrations lint install

install:
	pip install -r requirements.txt

migrate:
	python manage.py migrate

makemigrations:
	python manage.py makemigrations

run:
	python manage.py runserver

test:
	pytest

lint:
	python manage.py check
