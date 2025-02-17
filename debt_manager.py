from pymongo import MongoClient
import bcrypt
import datetime

# 連接 MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["debt_system"]

# 1️⃣ **註冊用戶**
def register_user(username, password, email):
    """ 註冊新用戶，並為該用戶建立專屬的欠款記錄表 """
    if db.users.find_one({"username": username}):
        return {"error": "用戶名已存在"}

    # 密碼加密
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # 存入用戶資訊
    user = {
        "username": username,
        "password": hashed_pw,
        "email": email
    }
    user_id = db.users.insert_one(user).inserted_id

    # **自動建立該用戶的欠款記錄表**
    user_collection_name = f"debts_{username}"  # 例如 debts_Alice
    db.create_collection(user_collection_name)

    return {"message": "註冊成功！", "user_id": str(user_id)}

# 2️⃣ **記錄欠款**
def add_debt(debtor_name, creditor_name, amount):
    """ 記錄欠款，並在雙方的專屬 Collection 內保存 """
    debtor = db.users.find_one({"username": debtor_name})
    creditor = db.users.find_one({"username": creditor_name})
    if not debtor or not creditor:
        return {"error": "用戶不存在"}

    debt_data = {
        "debtor": debtor_name,
        "creditor": creditor_name,
        "amount": amount,
        "status": "unpaid",
        "timestamp": datetime.datetime.utcnow()
    }

    # 在 **欠款人** 的 debts_xxx 集合中新增記錄
    debtor_collection = f"debts_{debtor_name}"
    db[debtor_collection].insert_one(debt_data)

    # 在 **貸方** 的 debts_xxx 集合中新增記錄
    creditor_collection = f"debts_{creditor_name}"
    db[creditor_collection].insert_one(debt_data)

    return {"message": "欠款已記錄！"}

# 3️⃣ **查詢某用戶的欠款**
def get_debts(username):
    """ 查詢某用戶的欠款與貸款狀況 """
    user = db.users.find_one({"username": username})
    if not user:
        return {"error": "用戶不存在"}

    collection_name = f"debts_{username}"
    debts = list(db[collection_name].find({}, {"_id": 0}))

    return {"debts": debts}

# 4️⃣ **還款**
def pay_debt(debtor_name, creditor_name, amount):
    """ 還款，並更新雙方的欠款記錄 """
    debtor = db.users.find_one({"username": debtor_name})
    creditor = db.users.find_one({"username": creditor_name})
    if not debtor or not creditor:
        return {"error": "用戶不存在"}

    debtor_collection = f"debts_{debtor_name}"
    creditor_collection = f"debts_{creditor_name}"

    # 找出最新一筆未還清的欠款
    debt = db[debtor_collection].find_one({"debtor": debtor_name, "creditor": creditor_name, "status": "unpaid"})
    if not debt:
        return {"error": "沒有未還清的欠款"}

    remaining_amount = debt["amount"]

    # 記錄還款交易
    transaction = {
        "debtor": debtor_name,
        "creditor": creditor_name,
        "amount": amount,
        "timestamp": datetime.datetime.utcnow()
    }
    db["transactions"].insert_one(transaction)

    # 更新欠款狀態
    if amount >= remaining_amount:
        db[debtor_collection].update_one({"_id": debt["_id"]}, {"$set": {"status": "paid", "amount": 0}})
        db[creditor_collection].update_one({"_id": debt["_id"]}, {"$set": {"status": "paid", "amount": 0}})
    else:
        db[debtor_collection].update_one({"_id": debt["_id"]}, {"$inc": {"amount": -amount}})
        db[creditor_collection].update_one({"_id": debt["_id"]}, {"$inc": {"amount": -amount}})

    return {"message": "還款成功！"}

# 5️⃣ **查詢還款紀錄**
def get_transactions(username):
    """ 查詢某用戶的還款紀錄 """
    user = db.users.find_one({"username": username})
    if not user:
        return {"error": "用戶不存在"}

    transactions = list(db["transactions"].find({"$or": [{"debtor": username}, {"creditor": username}]}, {"_id": 0}))

    return {"transactions": transactions}
