placebo
=======

[![codecov](https://codecov.io/gh/garnaat/placebo/branch/develop/graph/badge.svg?token=ukrsVmWxwv)](https://codecov.io/gh/garnaat/placebo)

Placebo allows you to mock boto3 calls that look just like normal calls but
actually have no effect at all.  It does this by allowing you to record a set
of calls and save them to a data file and then replay those calls later
(e.g. in a unit test) without ever hitting the AWS endpoints.

Installation
------------

~~~
$ pip install placebo
~~~

Quickstart
----------

Placebo uses the event mechanism in botocore to do most of its work.  To start
with, you need a boto3 Session object.

~~~ python
import boto3
import placebo

session = boto3.Session()
~~~

Once you have a Session object, you can tell placebo about the Session like
this:

~~~ python
pill = placebo.attach(session, data_path='/path/to/response/directory')
~~~

The ``data_path`` is a path to a directory where you want responses to be stored
or that contains previously recorded responses you want to playback.

The ``attach`` function returns an instance of a ``Pill`` object.  This object
will be used to control all recording and playback of requests for all clients
created by this session object.

The first thing you will probably want to do is record some requests.  To do
this, simply:

~~~ python
pill.record()
~~~

By default, the ``record`` method will cause all responses from all services to
be recorded to the ``data_path``.  If you are only interested in responses from
one certain services, you can limit the recording by passing in a list of
service names.

~~~ python
pill.record(services='ec2,iam')
~~~

This would limit to recording to responses from the ``ec2`` service and the
``iam`` service.  If you want to restrict recording to only certain operations
in a single service, you can do this:

~~~ python
pill.record(services='ec2', operations='DescribeInstances,DescribeKeyPairs')
~~~

From this point on, any clients that match the recording specification and are
created from the session will be placebo-aware.  To record responses, just
create the client and use it as you normally would.

~~~ python
aws_lambda = session.client('lambda')
aws_lambda.list_functions()
# ... more lambda calls ...
~~~

Each response will be saved as an individual JSON data file in the ``data_path``
path you specified when you attached the session.  Multiple responses from the
same service and operation are stored as separate files and will be replayed in
the same order on playback.

Later, to replay saved requests:

~~~ python
import boto3
import placebo

session = boto3.Session()
pill = placebo.attach(session, data_path='/path/to/response/directory')
pill.playback()
aws_lambda = session.client('lambda')
aws_lambda.list_functions()
# ... mocked response will be returned
~~~

#### Attaching to the default session

Sometimes, Placebo needs to be attached to the Boto3 [default session](http://boto3.readthedocs.io/en/latest/guide/session.html#default-session)
object.

To attach Placebo to the default session, it is necessary to explicitly set up
the default session by making a call to `boto3.setup_default_session()`.  The
default session is then accessible at `boto3.DEFAULT_SESSION`.

For example:

~~~ python
import boto3
import placebo

# Explicity set up the default session and attach Placebo to it.
boto3.setup_default_session()
session = boto3.DEFAULT_SESSION
pill = placebo.attach(session, data_path='/path/to/response/directory')
pill.record()

# Now make Boto3 calls using the default session.
client = boto3.client('ec2')
client.describe_images(DryRun=False)
~~~

This is particularly useful if you are writing tests for legacy code that
makes use of the Boto3 default session.

#### Using pickle

The responses can also be saved using pickle instead of JSON documents.
This can be useful to avoid serialization problems with complex types in
the responses.

To enable the pickle format:
```
pill = pill = placebo.attach(session, record_format="pickle")
```

#### Manual Mocking

You can also add mocked responses manually:

~~~ python
list_functions_response = [
    {
        "Version": "$LATEST",
        "CodeSha256": "I8Scq2g6ZKcPIvhKzvZqCiV4pDysxq4gZ+jLcMmDy5Y=",
        "FunctionName": "foobar",
        "MemorySize": 128,
        "CodeSize": 876521,
        "FunctionArn": "arn:aws:lambda:us-west-2:123456789012:function:foobar",
        "Handler": "foobar.handler",
        "Role": "arn:aws:iam::123456789012:role/foobar-role",
        "Timeout": 30,
        "LastModified": "2015-11-06T22:30:32.164+0000",
        "Runtime": "python2.7",
        "Description": "Foos all of the bars"
    }]

pill.save_response(service='lambda', operation='ListFunctions',
                   response_data=list_functions_response, http_response=200)
~~~

You can add additional responses to a particular operation and the responses
will be returned in order.  The final parameter is the HTTP response code which
is optional.  The default value is 200.

#### Usage as a decorator

Placebo also provides a decorator for easier usage.

First, you'll want to decorate your test method with `placebo_session` and include the `session` kwarg in your method, ex:
~~~ python
@placebo_session
def test_your_function(self, session):
    foo = Foo()
    arn = foo.create_iam_roles(session)
    self.assertEqual(arn, "arn:aws:iam::123:role/{}".format(foo.role_name))
~~~

Now, you'll be able to record the AWS interactions with an environment variable:
~~~ bash
$ PLACEBO_MODE=record nosetests tests.tests:TestFoo.test_create_iam_roles
~~~

You can optionally pass an AWS profile to use:
~~~ bash
$ PLACEBO_PROFILE=foo PLACEBO_MODE=record nosetests tests.tests:TestFoo.test_create_iam_roles
~~~

You can optionally set the record format to use:
```bash
$ PLACEBO_FORMAT=pickle PLACEBO_MODE=record nosetests tests.tests:TestFoo.test_create_iam_roles
```

In this example, it has created the following JSON blobs:
~~~
tests/placebo/TestFoo.test_create_iam_roles
tests/placebo/TestFoo.test_create_iam_roles/iam.CreateRole_1.json
tests/placebo/TestFoo.test_create_iam_roles/iam.GetRole_1.json
tests/placebo/TestFoo.test_create_iam_roles/iam.GetRolePolicy_1.json
tests/placebo/TestFoo.test_create_iam_roles/iam.PutRolePolicy_1.json
~~~

After the JSON has been created, simply drop the environment variables and re-run your test:
~~~ bash
$ nosetests tests.tests:TestFoo.test_create_iam_roles
~~~
