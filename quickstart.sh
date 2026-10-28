#!/bin/bash

cd "$HOME/kod3/art_major/" && \
source "$HOME/kod3/art_major/.venv/bin/activate" && \
cd "$HOME/kod3/art_major/artmajor"


python3 "$HOME/kod3/art_major/manage.py" makemigrations
python3 "$HOME/kod3/art_major/manage.py" migrate

python3 "$HOME/kod3/art_major/manage.py" collectstatic --noinput
python3 "$HOME/kod3/art_major/manage.py" runserver --settings=artmajor.settings.local

