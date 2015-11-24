placebo
=======

placebo provides a super-simple way to mock out botocore and boto3 clients to
return mock responses.  No network activity is incurred at all.

Installation
------------

```
$ pip install placebo
```

Quickstart
----------

After installing placebo, you can mock out a boto3 client like this:

```
import boto3
import placebo

session = boto3.Session()
lambda_client = session.client('lambda')
placebo.mock_client(lambda_client)
```

Once you have a mocked client, you can add mocked responses:

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

    
lambda_client.mock.add_response('ListFunctions', list_functions_response, 200)
```

You can then call the client and it will return the mocked responses:

```
>>> lambda_client.list_functions()
[{'CodeSha256': 'I8Scq2g6ZKcPIvhKzvZqCiV4pDysxq4gZ+jLcMmDy5Y=',
  'CodeSize': 876521,
  'Description': 'Foos all of the bars',
  'FunctionArn': 'arn:aws:lambda:us-west-2:123456789012:function:foobar',
  'FunctionName': 'foobar',
  'Handler': 'foobar.handler',
  'LastModified': '2015-11-06T22:30:32.164+0000',
  'MemorySize': 128,
  'Role': 'arn:aws:iam::123456789012:role/foobar-role',
  'Runtime': 'python2.7',
  'Timeout': 30,
  'Version': '$LATEST'}]
>>>
```

You can add additional responses to a particular operation and the responses
will be returned in order.  The final parameter is the HTTP response code which
is optional.  The default value is 200.


    
