placebo
=======

Placebo allows you to mock boto3 calls that look just like normal calls but
actually have no effect at all.  It does this by allowing you to record a set
of calls and save them to a data file and then replay those calls later
(e.g. in a unit test) without ever hitting the AWS endpoints.

Installation
------------

```
$ pip install placebo
```

Quickstart
----------

Placebo uses the event mechanism in botocore to do most of its work.  To start
with, you need a boto3 Session object.

```
import boto3
import placebo

session = boto3.Session()
```

Once you have a Session object, you can tell placebo about the Session like
this:

```
placebo.attach(session)
```

From this point on, all clients that are created from the session will be
placebo-aware.  To record a set of requests against that client:

```
lambda = session.client('lambda')
lambda.placebo.record()
lambda.list_functions()
... more lambda calls ...
lambda.placebo.save('my_saved_lambda_calls.json')
```

The recorded calls will now be saved to the file
``my_saved_lambda_calls.json``.  Later, to use saved requests in a unit test:

```
import boto3
import placebo

session = boto3.Session()
placebo.attach(session)
lambda = session.client('lambda')
lambda.placebo.begin()
lambda.list_functions()
... mocked response will be returned
```

You can also add mocked responses manually:

```
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

    
lambda.placebo.add_response('lambda', 'ListFunctions', list_functions_response, 200)
```

You can add additional responses to a particular operation and the responses
will be returned in order.  The final parameter is the HTTP response code which
is optional.  The default value is 200.


    
