# Getting Started: Quickstart Requirements
Now, let's get started!  

**Most quickstarts show a case where *everything works perfectly.***

**That is *not* what we're going to do today.** 

**We're going to break things horribly and enjoy it!**

**This is what testing is for.**

## System Requirements:
- Linux or Mac OS X with python 2.6+ or 2.7 installed and pycurl
- Do not use a virtualenv (or have it custom configured to find libcurl)

# Quickstart Part 0: Setting Up a Sample REST Service
In order to get started with PyRestTest, we will need a REST service with an API to work with.

Fortunately, there is a small RESTful service included with the project. 

Let's **grab a copy of the code** to start:
```shell
git clone https://github.com/svanoort/pyresttest.git
```

Then we'll **install the necessary dependencies** to run it (Django and Django Tastypie):
```shell
sudo pip install 'django >=1.6, <1.7' django-tastypie
```
Now **we start a test server in one terminal** (on default port 8000) with some preloaded data, and we will test in a second terminal:
```shell
cd pyresttest/pyresttest/testapp
python manage.py testserver test_data.json
```

**If you get an error like this**, it's because you're using Python 2.6, and are trying to run a Django version not compatible with that:
```
Traceback (most recent call last):
  File "/usr/bin/django-admin.py", line 2, in <module>
    from django.core import management
  File "/usr/lib64/python2.6/site-packages/django/core/management/__init__.py", line 68
    commands = {name: 'django.core' for name in find_commands(__path__[0])}
```

This is easy enough to fix though by installing a compatible Django version:
```shell
sudo pip uninstall -y django django-tastypie
sudo pip install 'django >=1.6, <1.7' django-tastypie
```
**Before going deeper, let's make sure that server works okay... in our second terminal, we run this:**
```shell
curl -s http://localhost:8000/api/person/2/ | python -m json.tool
```

**If all is good, we ought to see a result like this:**
```json
{
    "first_name": "Leeroy", 
    "id": 2, 
    "last_name": "Jenkins", 
    "login": "jenkins", 
    "resource_uri": "/api/person/2/"
}
```

**Now, we've got a small but working REST API for PyRestTest to test on!**

# Quickstart Part 1: Our First (Smoke) Test
In our second terminal, we're going to create a basic REST smoketest, which can be used to test the server came up cleanly and works.

Pop up ye olde text editor of choice and save this to a file named 'test.yaml':

```yaml
---
- config:
    - testset: "Quickstart app tests"

- test:
    - name: "Basic smoketest"
    - url: "/api/people/"
```

And when we run it:
```shell
resttest.py http://localhost:8000 test.yaml
```

**OOPS!**  As the more observant people will notice, **we got the API URL wrong**, and the test failed, showing the unexpected 404, and reporting the test name.  At the end we see the summary, by test group ("Default" is exactly like what it sounds like).  

**Let's fix that, add a test group name, and re-run it!**
```yaml
---
- config:
    - testset: "Quickstart app tests"

- test:
    - group: "Quickstart"
    - name: "Basic smoketest"
    - url: "/api/person/"
```

Ahh, *much* better!  But, that's very basic, surely we can do *better?*


# Quickstart Part 2: Functional Testing - Create/Update/Delete
Let's build this out into a full test scenario, creating and deleting a user:

We're going to add a create for a new user, that scoundrel Gaius Baltar:
```yaml
---
- config:
    - testset: "Quickstart app tests"

- test:
    - group: "Quickstart"
    - name: "Basic smoketest"
    - url: "/api/person/"

- test:
    - group: "Quickstart"
    - name: "Create a person"
    - url: "/api/person/10/"
    - method: "PUT"
    - body: '{"first_name": "Gaius","id": 10,"last_name": "Baltar","login": "baltarg"}'
```
... and when we run it, it fails (500 error).  That sneaky lowdown tried to sneak in without a Content-Type so the server knows what he is. 

**Let's fix it...**

```yaml
- test:
    - group: "Quickstart"
    - name: "Create a person"
    - url: "/api/person/10/"
    - method: "PUT"
    - body: '{"first_name": "Gaius","id": 10,"last_name": "Baltar","login": "baltarg"}'
    - headers: {'Content-Type': 'application/json'}
```

... and now both tests will pass. 
Then let's add a test the person is really there after:

```yaml
---
- config:
    - testset: "Quickstart app tests"

- test:
    - group: "Quickstart"
    - name: "Basic smoketest"
    - url: "/api/person/"

- test:
    - group: "Quickstart"
    - name: "Create a person"
    - url: "/api/person/10/"
    - method: "PUT"
    - body: '{"first_name": "Gaius","id": 10,"last_name": "Baltar","login": "baltarg"}'
    - headers: {'Content-Type': 'application/json'}

- test:
    - group: "Quickstart"
    - name: "Make sure Mr Baltar was added"
    - url: "/api/person/10/"
```

**Except there is a problem with this... the third test will pass if Baltar already existed in the database.  Let's test he wasn't there beforehand...**

```yaml
---
- config:
    - testset: "Quickstart app tests"

- test:
    - group: "Quickstart"
    - name: "Make sure Mr Baltar ISN'T there to begin with"
    - url: "/api/person/10/"
    - expected_status: [404]

- test:
    - group: "Quickstart"
    - name: "Basic smoketest"
    - url: "/api/person/"

- test:
    - group: "Quickstart"
    - name: "Create a person"
    - url: "/api/person/10/"
    - method: "PUT"
    - body: '{"first_name": "Gaius","id": 10,"last_name": "Baltar","login": "baltarg"}'
    - headers: {'Content-Type': 'application/json'}

- test:
    - group: "Quickstart"
    - name: "Make sure Mr Baltar is there after we added him"
    - url: "/api/person/10/"
```

**Much better, now the first test fails... so, let's add a delete for that user at the end of the test, and check he's really gone.**

```yaml
---
- config:
    - testset: "Quickstart app tests"

- test:
    - group: "Quickstart"
    - name: "Make sure Mr Baltar ISN'T there to begin with"
    - url: "/api/person/10/"
    - expected_status: [404]

- test:
    - group: "Quickstart"
    - name: "Basic smoketest"
    - url: "/api/person/"

- test:
    - group: "Quickstart"
    - name: "Create a person"
    - url: "/api/person/10/"
    - method: "PUT"
    - body: '{"first_name": "Gaius","id": 10,"last_name": "Baltar","login": "baltarg"}'
    - headers: {'Content-Type': 'application/json'}

- test:
    - group: "Quickstart"
    - name: "Make sure Mr Baltar is there after we added him"
    - url: "/api/person/10/"

- test:
    - group: "Quickstart"
    - name: "Get rid of Gaius Baltar!"
    - url: "/api/person/10/"
    - method: 'DELETE'

- test:
    - group: "Quickstart"
    - name: "Make sure Mr Baltar ISN'T there after we deleted him"
    - url: "/api/person/10/"
    - expected_status: [404]
```

**And now we have a full lifecycle test of creating, fetching, and deleting a user via the API.**

Basic authentication is supported:

```yaml
---
- config:
    - testset: "Quickstart authentication test"

- test:
    - name: "Authentication using basic auth"
    - url: "/api/person/"
    - auth_username: "foobar"
    - auth_password: "secret"
    - expected_status: [200]
```

**This is just a starting point,** see the [advanced guide](advanced_guide.md) for the advanced features (templating, generators, content extraction, complex validation).