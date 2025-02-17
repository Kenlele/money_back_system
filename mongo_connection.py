from pymongo import MongoClient

client=MongoClient("mongodb://localhost:27017/")

db=client["mydatabase"]

collection =db["users"]

user_data={"name":"ken" , "age":30}
collection.insert_one(user_data)

print("成功插入數據到mongodb")

