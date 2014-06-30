cd readthedocs
if [ $# -eq 0 ]; then
    path=./
else
    path=$*
fi
DJANGO_SETTINGS_MODULE=settings.test ./manage.py test --logging-clear-handlers $path
exit=$?
cd -
exit $exit
