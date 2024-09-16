import sqlite3
from flask_bcrypt import Bcrypt
conn=sqlite3.connect("instance/Cordinates.db")


def PrintallUser():
    query='SELECT * FROM tbl_user'
    print("\nALL USERS FROM DB\n".center(50))
    for data in conn.execute(query):
       print("NAME:",data[1])
       print("IP:",data[7])
       print("\n")


def ChangeString():
    print("UPDATE DASHBOARD".center(50))
    username=input("Enter a username:")
    query=f''' SELECT * FROM tbl_user WHERE username=="{username}" '''
    p=False
    id_=None
    for data in conn.execute(query):
        id=data[0]
        p=True 
    if p:
       print("\nYou are succcessfuly log in\n")
       option=input("Do you want make the IP address as null(Y/N):")
       if option.lower() == "y":
           conn.execute(f"UPDATE tbl_user SET ip = '{None}' WHERE username =='{username}' ")
           conn.commit()
           print("\n\n Updated successfully")
       else:
            exit()
    else:
        print("\nSorry ! Check your password and username\n")




while True:    
    PrintallUser()
    ChangeString()

conn.close()

