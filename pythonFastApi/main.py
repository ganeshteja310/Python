import io
import sqlite3
import tempfile
import psycopg2
import json
import threading
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from typing import Dict, List, Any
from pydantic import BaseModel
import jwt
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta

SECRET_KEY = "authkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
class TableData(BaseModel):
    table_name: str
    rows: List[Dict[str, Any]]

class AllTablesDataResponse(BaseModel):
    data: Dict[str, TableData]

def create_access_token(data: dict, expires: timedelta = None):
    to_encode = data.copy()
    if expires:
        expire = datetime.utcnow() + expires
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
def get_user_from_db(username: str,password: str):
    conn = connect_to_postgres()
    cursor = conn.cursor()
    cursor.execute("SELECT username, email FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    print("verifying User details are available or not ")
    cursor.close()
    conn.close()
    if user:
        return {"username": user[0], "password": user[1]}
    return None

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    print("Token retriving ")
    userdetails = get_user_from_db(form_data.username,form_data.password)
    if form_data.username == userdetails["username"]  and form_data.password == userdetails["password"]:
        print("user details valid")
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": form_data.username}, expires=access_token_expires
        )
        print("token generated success")
        return {"access_token": access_token, "token_type": "bearer"}
    else:
        raise HTTPException(status_code=401, detail="Incorrect username or  password")

def connect_to_postgres():
    print("connecting to DB...")
    return psycopg2.connect(
        host="localhost",
        port="5432",
        database="sample",
        user="postgres",
        password="postgres"
    )

def create_table_in_postgres(table_name: str, columns: List[str]):
    conn = connect_to_postgres()
    cursor = conn.cursor()
    print("table creation in progres..")
    column_definitions = ", ".join([f"{col_name} TEXT" for col_name in columns])
    create_table_query = f"CREATE TABLE IF NOT EXISTS {table_name} ({column_definitions});"
    cursor.execute(create_table_query)
    conn.commit()
    cursor.close()
    conn.close()

def insert_data_into_postgres(table_name: str, rows: List[tuple], column_names: List[str]):
    conn = connect_to_postgres()
    cursor = conn.cursor()
    print("Inserting data")
    placeholders = ', '.join(['%s'] * len(column_names))
    insert_query = f"INSERT INTO {table_name} ({', '.join(column_names)}) VALUES ({placeholders});"
    cursor.executemany(insert_query, rows)
    conn.commit()
    cursor.close()
    conn.close()

def transfer_table_data(table_name: str, rows: List[tuple], column_names: List[str]):
    create_table_in_postgres(table_name, column_names)
    insert_data_into_postgres(table_name, rows, column_names)

def get_all_tables_data() -> Dict[str, TableData]:
    conn = connect_to_postgres()
    cursor = conn.cursor()
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
    tables = cursor.fetchall()
    data = {}
    for (table_name,) in tables:
        cursor.execute(f"SELECT * FROM {table_name};")
        rows = cursor.fetchall()
        cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}';")
        columns = [row[0] for row in cursor.fetchall()]
        rows_as_dicts = [dict(zip(columns, row)) for row in rows]
        data[table_name] = TableData(table_name=table_name, rows=rows_as_dicts)
    cursor.close()
    conn.close()
    return data

@app.post("/get_sqlite_data/", response_model=AllTablesDataResponse)
async def upload_and_transfer(file: UploadFile = File(...), token: str = Depends(verify_token)) -> AllTablesDataResponse:
    try:
        file_contents = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as temp_file:
            temp_file.write(file_contents)
            temp_file.seek(0)
            sqlite_conn = sqlite3.connect(temp_file.name)
            sqlite_cursor = sqlite_conn.cursor()
            sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = sqlite_cursor.fetchall()
            threads = []
            for (table_name,) in tables:
                sqlite_cursor.execute(f"SELECT * FROM {table_name};")
                rows = sqlite_cursor.fetchall()
                if rows:
                    sqlite_cursor.execute(f"PRAGMA table_info({table_name});")
                    columns_info = sqlite_cursor.fetchall()
                    column_names = [col[1] for col in columns_info]
                    thread = threading.Thread(target=transfer_table_data, args=(table_name, rows, column_names))
                    threads.append(thread)
                    thread.start()
                else:
                    print("No rows found for this table")
            for thread in threads:
                thread.join()
            all_data = get_all_tables_data()

        return AllTablesDataResponse(data=all_data)

    except Exception as e:
        print("An error occurred")
        raise HTTPException(status_code=500, detail="Internal Server Error")
