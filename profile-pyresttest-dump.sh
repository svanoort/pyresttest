python3 -m cProfile -o github-py3.out pyresttest/resttest.py https://api.github.com examples/github_api_smoketest.yaml

# Use the Django test app to benchmark
python pyresttest/testapp/manage.py testserver pyresttest/testapp/test_data.json &
DJANGO_PROCESS=$!
sleep 5
python3 -m cProfile -o content-py3.out pyresttest/resttest.py http://localhost:8000 pyresttest/content-test.yaml
kill -9 $DJANGO_PROCESS

# Full profiler dump
# python -m cProfile -o github_api_dump.out pyresttest/resttest.py https://api.github.com examples/github_api_smoketest.yaml