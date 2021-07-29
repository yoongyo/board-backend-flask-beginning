from datetime import datetime

# print(str(datetime.now().replace(microsecond=0)))

print(datetime.strptime(datetime.now().strftime('%Y-%m-%d %H:%M'), '%Y-%m-%d %H:%M'))