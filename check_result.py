import sqlite3
from datetime import datetime


def check_result(request,id):
    try:
        # Connect to SQLite database
        conn = sqlite3.connect('tasks.db')
        cursor = conn.cursor()

        # Get all pending tasks
        cursor.execute(f'''
            SELECT  date,time,status,result
            FROM tasks
            WHERE  task_id = {id}
        ''')
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        return str(f"status : {result[2]}  <br/> datetime : {result[0],result[1]} <br/> text: {result[3]}")
        # return tasks[0]
    except Exception as e:
        print(e)