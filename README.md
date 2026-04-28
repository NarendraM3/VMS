# Quadrant Visitor Management System

A role-based visitor management application built for Quadrant Technologies. This project combines static frontend pages with AWS serverless backend services to manage visitor requests, Aadhaar uploads, approval workflows, and gate access tracking.

## Project Summary

This system is designed to manage visitor entry for an enterprise environment. It supports three roles:

- **Employee**: register visitors, upload Aadhaar documents, and view their visitor list.
- **Admin**: review visitor requests, approve or reject visits, reschedule appointments, export visitor data, and manage internal users.
- **Security**: validate visitor gate entry, approve or deny arrival, and record visitor exit times.

The frontend is built using static HTML, CSS, and JavaScript. The backend is implemented as an AWS Lambda function that stores visitor and user records in DynamoDB and saves Aadhaar uploads in S3.

## What this project does

- Allows employees to submit visitor requests with Aadhaar and visit details.
- Generates presigned S3 upload URLs so visitors can securely upload Aadhaar documents directly to S3.
- Saves visitor records in DynamoDB and links uploaded Aadhaar files to the correct visitor.
- Provides admin controls for approving, rejecting, or rescheduling visitors.
- Enables security staff to mark visitor arrival and exit times.
- Supports a chatbot assistant lambda for querying visitor records with natural language.

## Key Features

- Multi-role portal with separate employee, admin, and security experiences.
- Presigned S3 upload/download flow for Aadhaar documents.
- Visitor registration and status workflow.
- Admin analytics, search, filter, and CSV export capabilities.
- EmailJS notification support in the frontend dashboards.
- Optional chatbot assistant for natural-language visitor queries.

## AWS Services Used

This repo uses the following AWS services:

- **AWS Lambda**: Runs the backend logic in `lambda functions.py` and optionally `Chatbot_lambda_function.py`.
- **Amazon API Gateway**: Exposes HTTP REST endpoints for the frontend to call.
- **Amazon DynamoDB**: Stores internal users and visitor records in two tables:
  - `Employees`
  - `Visitors`
- **Amazon S3**: Stores Aadhaar documents uploaded by employees via presigned URLs.
- **IAM permissions**: The Lambda function requires permissions to read/write DynamoDB and generate presigned URLs for S3.

## AWS Resource Details

### DynamoDB Tables

#### `Employees`
- Partition key: `emp_id` (String)
- Stores internal users with fields:
  - `emp_id`
  - `name`
  - `role`

#### `Visitors`
- Partition key: `visitor_id` (String)
- Stores visitor data and lifecycle fields:
  - `visitor_id`
  - `name`
  - `aadhaar`
  - `email`
  - `mobile`
  - `date`
  - `time`
  - `purpose`
  - `emp_name`
  - `emp_id`
  - `status`
  - `rescheduled_date`
  - `rescheduled_time`
  - `aadhaar_key`
  - `reg_time`
  - `in_time`
  - `out_time`

### S3 Bucket

- Bucket name: `visitor-images-narendra`
- Aadhaar uploads are stored with keys like `aadhaar/<visitor_id>.<ext>`.
- Lambda generates presigned PUT URLs to allow secure direct uploads from the browser.
- Lambda also generates presigned GET URLs for admin/security to view Aadhaar documents.

### Lambda and API Gateway

- `lambda functions.py` handles API routes and backend logic.
- `Chatbot_lambda_function.py` is a separate optional assistant that answers visitor-related queries.
- API Gateway forwards requests to Lambda and enables CORS for frontend origin.

## Project Structure

```text
QT project/
|-- Admin1.html
|-- Chatbot_lambda_function.py
|-- Main employee.html
|-- Main security.html
|-- Web.html
|-- lambda functions.py
|-- README.md
```

## File Guide

- `Web.html`: main landing page with role selection.
- `Admin1.html`: admin dashboard for visitor approvals, rescheduling, exports, and chatbot.
- `Main employee.html`: employee portal for registering visitors and uploading Aadhaar.
- `Main security.html`: security portal for gate entry validation and visitor exit.
- `lambda functions.py`: primary backend logic for API routes, DynamoDB, and S3.
- `Chatbot_lambda_function.py`: natural-language assistant lambda for visitor queries.

## How it Works

### Employee Flow

1. Employee enters their name and employee ID.
2. Employee fills visitor details and Aadhaar number.
3. The app requests a presigned S3 upload URL from `/upload-url`.
4. The Aadhaar file is uploaded directly to S3.
5. The visitor record is stored in DynamoDB with the `aadhaar_key` reference.

### Admin Flow

1. Admin logs in and loads visitors from `/visitors` or `/admin`.
2. Admin can approve, reject, or reschedule visitors using `/approve` and `/register`.
3. Admin can view Aadhaar documents through the presigned GET route `/aadhaar`.
4. Admin can add or remove internal users through `/user`.

### Security Flow

1. Security loads visitor schedules.
2. Security approves entry or rejects arrival by calling `/approve`.
3. Security records visitor exits using `/approve` with `out_time`.

## API Routes

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/user` | Retrieve internal users |
| `POST` | `/user` | Create a new internal user |
| `DELETE` | `/user` | Delete a user by `emp_id` |
| `GET` | `/visitors` | List visitor records |
| `GET` | `/admin` | Alias for visitor list |
| `POST` | `/register` | Register a visitor |
| `PUT` | `/register` | Reschedule a visitor |
| `POST` | `/approve` | Update visitor status and in/out times |
| `GET` | `/upload-url` | Generate Aadhaar upload URL |
| `GET` | `/aadhaar` | Generate Aadhaar download URL |
| `GET` | `/presigned` | Alternate Aadhaar download route |
| `POST` | `/aadhaar-key` | Save Aadhaar key to visitor record |

## AWS Setup Guide

1. Create the DynamoDB tables `Employees` and `Visitors`.
2. Create the S3 bucket `visitor-images-narendra`.
3. Deploy `lambda functions.py` as an AWS Lambda function.
4. Configure API Gateway routes and link them to Lambda.
5. Enable CORS for the frontend origin.
6. Update the `API_BASE` URL in the HTML pages to use your deployed API.

## Local Run Guide

- The frontend is static and can be opened directly in any browser.
- For full AWS integration, host the frontend on S3 or another static host and connect it to your deployed API.
- The backend requires AWS credentials with DynamoDB and S3 access.

## Known Limitations

- No production authentication; login is handled client-side.
- Visitor email validation is limited to `@gmail.com`.
- Aadhaar documents are stored in S3 and shared via presigned URLs without additional encryption.
- Configuration values are hard-coded rather than using environment variables.
