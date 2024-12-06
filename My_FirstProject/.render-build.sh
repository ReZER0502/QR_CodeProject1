
pip install -r requirements.txt

python manage.py migrate
python manage.py collectstatic --noinput

chmod +x .render-build.sh
