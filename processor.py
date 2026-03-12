import time

logs=[]

def process(log):

    try:

        client,timestamp,level,msg=log.split("|")

        logs.append((float(timestamp),client,level,msg))

        logs.sort()

        latest=logs[-1]

        print(
            f"[{time.strftime('%H:%M:%S',time.localtime(latest[0]))}] "
            f"{latest[1]} {latest[2]} {latest[3]}"
        )

    except:
        pass