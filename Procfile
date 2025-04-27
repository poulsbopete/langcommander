web: mkdir -p /var/pids && exec gunicorn app:application \
    --bind 0.0.0.0:$PORT \
    --pid /var/pids/web.pid