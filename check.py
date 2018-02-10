
from passlib.apps import custom_app_context as pwd_context


password = "casds3t"
password_confirmed = "casds3t"

username = "melon"

# print(pwd_context.verify(password, password_confirmed, user=username))
# print((pwd_context.verify(password, password_confirmed, user=username) == False)

result = pwd_context.verify(password, password_confirmed) #, user=username)

