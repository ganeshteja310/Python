
# FastAPI Application with JWT Authentication

This app allows you to upload a `.db` (SQLite) file, transfer its data into a PostgreSQL database, and retrieve all the data as JSON. The application also supports JWT authentication for secure API access.

## Features

- **JWT Authentication**: Secure the `/get_sqlite_data/` endpoint using a token-based authentication system (JWT).
- **SQLite to PostgreSQL Transfer**: Upload a SQLite file, and the tables and their data will be automatically created and transferred to a PostgreSQL database.
- **Multithreaded Data Transfer**: Each table’s data is transferred in a separate thread for better performance.
- **JSON Response**: After the data transfer, all the table data is returned as JSON.
  
# Endpoints

### 1. `/token` (POST)
Generates a JWT access token for authenticated requests.

- **Parameters**: `username`, `password` (sent as input data)
- **Response**: 
  ```json
  {
      "access_token": "sample-token",
      "token_type": "bearer"
  }
  ```

### 2. `/get_sqlite_data/` (POST)
Uploads a SQLite `.db` file, transfers its contents to a PostgreSQL database, and returns the data in JSON format.

- **Headers**: 
  - `Authorization`: Bearer `<Generated Token>`
  
- **Request**: 
  - Upload file (`.db`)

- **Response**: JSON object containing all the transferred tables and their data.

### Example Response
```json
{
    "data": {
        "table_name_1": {
            "table_name": "table_name_1",
            "rows": [
                {"column_1": "value_1", "column_2": "value_2"},
                ...
            ]
        },
        "table_name_2": {
            "table_name": "table_name_2",
            "rows": [
                {"column_1": "value_1", "column_2": "value_2"},
                ...
            ]
        }
    }
}
```

## How to Run

### 1. Install Dependencies
pip install fastapi uvicorn psycopg2 pydantic 
```

### 2. Set up PostgreSQL

Ensure you have PostgreSQL running locally, and create a sample database:
```sql
CREATE DATABASE sample;
```

### 3. Run the Application

```bash
uvicorn main:app --reload
```

### 4. Use the Application

- **Get Token**: Use Postman or `cURL` to retrieve the access token:
  ```bash
  curl -X POST "http://127.0.0.1:8000/token" -F "username=myuser" -F "password=mypassword"
  ```

- **Upload and Transfer Data**: After obtaining the token, use it in the `Authorization` header to upload a SQLite database:
  ```bash
  curl -X POST "http://127.0.0.1:8000/get_sqlite_data/"   -H "Authorization: Bearer <your_token>"   -F "file=@yourfile.db"
  ```

## Environment Variables

- `SECRET_KEY`: Secret key used for JWT encoding/decoding.
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Time in minutes for token expiration.
- `DATABASE_URL`: PostgreSQL connection URL.

