python -m cProfile -s tottime pyresttest/resttest.py http://jsonplaceholder.typicode.com jsontest.yaml > jsontest-tots.txt
python -m cProfile -s cumtime pyresttest/resttest.py http://jsonplaceholder.typicode.com jsontest.yaml > jsontest-cum.txt

# Use the Django test app to benchmark
python pyresttest/testapp/manage.py testserver pyresttest/testapp/test_data.json &
DJANGO_PROCESS=$!
sleep 5
python -m cProfile -s tottime pyresttest/resttest.py http://localhost:8000 pyresttest/content-test.yaml > contenttest-tot.txt
kill -9 $DJANGO_PROCESS

# Clean slate for cumulative call time
python pyresttest/testapp/manage.py testserver pyresttest/testapp/test_data.json &
DJANGO_PROCESS=$!
sleep 5
python -m cProfile -s cumtime pyresttest/resttest.py http://localhost:8000 pyresttest/content-test.yaml > contenttest-cum.txt
kill -9 $DJANGO_PROCESS
