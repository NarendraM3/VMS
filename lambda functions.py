import json
import boto3
import uuid
import traceback

dynamodb = boto3.resource('dynamodb')
employees_table = dynamodb.Table('Employees')
visitors_table  = dynamodb.Table('Visitors')
s3_client       = boto3.client('s3', region_name='ap-south-1')

S3_BUCKET = "visitor-images-narendra"

# ====================== CORS HEADERS ======================
CORS_HEADERS = {
    'Access-Control-Allow-Origin': 'https://visitor-management-frontend.s3.ap-south-1.amazonaws.com',
    'Access-Control-Allow-Methods': 'OPTIONS, GET, POST, PUT, DELETE',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Amz-Date, X-Api-Key, X-Amz-Security-Token'
}

def make_response(status_code, body):
    """Always include CORS headers on every response"""
    return {
        'statusCode': status_code,
        'headers': CORS_HEADERS,
        'body': json.dumps(body) if isinstance(body, (dict, list)) else str(body)
    }


def lambda_handler(event, context):
    print("=== EVENT ===")
    print(json.dumps(event, default=str))

    request_context = event.get('requestContext', {})
    http            = request_context.get('http', {})
    http_method     = event.get('httpMethod') or http.get('method', 'GET')

    raw_path = (
        event.get('rawPath') or
        event.get('path') or
        '/' + (event.get('pathParameters') or {}).get('proxy', '')
    ).rstrip('/')

    print(f"Method: {http_method}, Path: {raw_path}")

    # ── Handle Preflight OPTIONS Request (fixes CORS) ───────
    if http_method == 'OPTIONS':
        print("Handling OPTIONS preflight")
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': ''
        }

    try:
        # ── /user ─────────────────────────────────────────────
        if raw_path in ['/user', '/user/']:
            if http_method == 'GET':
                response = employees_table.scan()
                return make_response(200, response.get('Items', []))

            elif http_method == 'POST':
                body = json.loads(event.get('body') or '{}')
                item = {
                    'emp_id': body.get('regEmpId') or body.get('emp_id'),
                    'name':   body.get('regName')  or body.get('name'),
                    'role':   body.get('regRole')  or body.get('role', 'employee')
                }
                if not item['emp_id'] or not item['name']:
                    raise ValueError("emp_id and name are required")
                employees_table.put_item(Item=item)
                return make_response(200, {'message': 'User registered successfully'})

            elif http_method == 'DELETE':
                body = json.loads(event.get('body') or '{}')
                emp_id = body.get('emp_id', '')
                if not emp_id:
                    return make_response(400, {'error': 'emp_id required'})
                employees_table.delete_item(Key={'emp_id': emp_id})
                return make_response(200, {'message': f'User {emp_id} removed successfully'})

        # ── /visitors and /admin ───────────────────────────────
        elif raw_path in ['/visitors', '/admin']:
            if http_method == 'GET':
                response = visitors_table.scan()
                return make_response(200, response.get('Items', []))

        # ── /register ─────────────────────────────────────────
        elif raw_path == '/register':
            if http_method == 'POST':
                body = json.loads(event.get('body') or '{}')
                visitor_id = body.get('visitor_id', f"QT{str(uuid.uuid4())[:8].upper()}")

                item = {
                    'visitor_id':       visitor_id,
                    'name':             body.get('name'),
                    'aadhaar':          body.get('aadhaar'),
                    'email':            body.get('email', 'N/A'),
                    'date':             body.get('date'),
                    'time':             body.get('time'),
                    'purpose':          body.get('purpose'),
                    'emp_name':         body.get('emp_name'),
                    'emp_id':           body.get('emp_id'),
                    'status':           body.get('status', 'pending'),
                    'rescheduled_date': body.get('rescheduled_date', ''),
                    'rescheduled_time': body.get('rescheduled_time', ''),
                    'aadhaar_key':      body.get('aadhaar_key', ''),
                    'reg_time':         body.get('reg_time', '')
                }
                visitors_table.put_item(Item=item)
                return make_response(200, {
                    'message': 'Visitor registered successfully',
                    'visitor_id': visitor_id
                })

            elif http_method == 'PUT':
                body = json.loads(event.get('body') or '{}')
                visitors_table.update_item(
                    Key={'visitor_id': body['visitor_id']},
                    UpdateExpression="SET #d=:d, #t=:t, #p=:p, rescheduled_date=:rd, rescheduled_time=:rt",
                    ExpressionAttributeNames={'#d': 'date', '#t': 'time', '#p': 'purpose'},
                    ExpressionAttributeValues={
                        ':d':  body['newDate'],
                        ':t':  body['newTime'],
                        ':p':  body.get('newPurpose', body.get('purpose', '')),
                        ':rd': body['newDate'],
                        ':rt': body['newTime']
                    }
                )
                return make_response(200, {'message': 'Rescheduled successfully'})

        # ── /approve ──────────────────────────────────────────
        elif raw_path == '/approve':
            if http_method == 'POST':
                body = json.loads(event.get('body') or '{}')
                update_expr = "SET #status = :s"
                values      = {':s': body['status']}
                names       = {'#status': 'status'}

                if 'in_time' in body:
                    update_expr += ", in_time = :it"
                    values[':it'] = body['in_time']
                if 'out_time' in body:
                    update_expr += ", out_time = :ot"
                    values[':ot'] = body['out_time']

                visitors_table.update_item(
                    Key={'visitor_id': body['visitor_id']},
                    UpdateExpression=update_expr,
                    ExpressionAttributeNames=names,
                    ExpressionAttributeValues=values
                )
                return make_response(200, {'message': 'Status updated successfully'})

        # ── /upload-url → presigned PUT URL ───────────────────
        elif raw_path == '/upload-url':
            if http_method == 'GET':
                params     = event.get('queryStringParameters') or {}
                visitor_id = params.get('visitor_id', '')
                file_ext   = params.get('ext', 'jpg')

                if not visitor_id:
                    return make_response(400, {'error': 'visitor_id required'})

                aadhaar_key = f"aadhaar/{visitor_id}.{file_ext}"

                presigned_put = s3_client.generate_presigned_url(
                    'put_object',
                    Params={
                        'Bucket': S3_BUCKET,
                        'Key':    aadhaar_key
                    },
                    ExpiresIn=300
                )
                return make_response(200, {
                    'upload_url': presigned_put,
                    'aadhaar_key': aadhaar_key
                })

        # ── /aadhaar → presigned GET URL ──────────────────────
        elif raw_path in ['/aadhaar', '/presigned']:
            if http_method == 'GET':
                params     = event.get('queryStringParameters') or {}
                visitor_id = params.get('visitor_id', '')

                if not visitor_id:
                    return make_response(400, {'error': 'visitor_id required'})

                result      = visitors_table.get_item(Key={'visitor_id': visitor_id})
                item        = result.get('Item', {})
                aadhaar_key = item.get('aadhaar_key', '')

                print(f"DEBUG - visitor_id: {visitor_id}, aadhaar_key: '{aadhaar_key}'")

                if not aadhaar_key:
                    return make_response(404, {'error': 'No Aadhaar document found for this visitor'})

                presigned_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': S3_BUCKET, 'Key': aadhaar_key},
                    ExpiresIn=600
                )
                return make_response(200, {'presigned_url': presigned_url})

        # ── /aadhaar-key → save S3 key to DynamoDB ────────────
        elif raw_path == '/aadhaar-key':
            if http_method == 'POST':
                body        = json.loads(event.get('body') or '{}')
                visitor_id  = body.get('visitor_id', '')
                aadhaar_key = body.get('aadhaar_key', '')

                if not visitor_id or not aadhaar_key:
                    return make_response(400, {'error': 'visitor_id and aadhaar_key required'})

                visitors_table.update_item(
                    Key={'visitor_id': visitor_id},
                    UpdateExpression="SET aadhaar_key = :k",
                    ExpressionAttributeValues={':k': aadhaar_key}
                )
                return make_response(200, {'message': 'Aadhaar key saved'})

        # ── Route not found ────────────────────────────────────
        return make_response(404, {'error': f'Route not found: {http_method} {raw_path}'})

    except Exception as e:
        print("=== ERROR ===")
        print(traceback.format_exc())
        return make_response(500, {
            'error': str(e),
            'message': 'Internal server error. Check CloudWatch Logs.'
        })