import json
import sys
import smtplib
import re


items = ['Category', 'Distance', 'Duration', 'Start']
unts = {items[1]:'km', items[2]:'hodin'}

# it's going to reset by data from config.json:
# MAIL:
SMTP = "smtp.seznam.cz"
SMTPPORT = 587
CONFIG = "config.json"



"""config.json ->
example:
{"mail": {"smtp": "smtp.seznam.cz", "port":587, "psw": "passwd",
          "fromWh":"somebody@seznam.cz", "toWh":"somebody@gmail.com"},
  "alarms": [{"counted": 45.78, "Message": "Subject: Your cycling\n\n Time for servis",
             "Category": "Cycling", "Distance": 800},
             {"Message": "Subject: Super!\n\n another 30km running -> Relax!",
             "Category": "Running", "Distance": 30},
             {"counted": 2.505, "Message": "Subject: Great!\n\n another 10 hours of running -> go to swim!",
              "Duration": 10, "Category": "Running"}],
  "version": "sportstracklive01",
  "data": ".../Dropbox/Sport/MyActivities.txt"}

- put this code 'sportstracklive.py' and config 'config.json' in the same folder
- ensure the supply of informations about your activities ('zapier.com': gmail -> dropbox)
- create a dedicated mail account and set smtp+port+passwd to your 'config.json'
- set alarms in your config (Message, Category and Distance/Duration). Distance -> number of km,
  Duration -> number of hours.
- enjoy!
"""

'''
todo: upravit email fci a nastavit odesilani pri dosazeni alarmu
'''



def send_email(user, pwd, recipient, subjectbody):
    # TO = recipient if type(recipient) is list else [recipient]
    TO = [recipient] #only one
    TEXT = subjectbody


    # Prepare actual message
    message = """From: %s\nTo: %s\n%s""" % (user, ", ".join(TO), TEXT)

    try:
        server = smtplib.SMTP(SMTP, SMTPPORT)
        server.ehlo()
        server.starttls()
        server.login(user, pwd)
        server.sendmail(user, TO, message)
        server.close()
        # print('successfully sent the mail')
    except:
        print("failed to send mail")



def get_num(x):
    """get_num('123.45km') -> 123.45"""
    return float(''.join(ele for ele in x if ele.isdigit() or ele == '.'))

def get_time(x):
    l = [*(map(lambda e: get_num(e),x.split()))]
    if len(l)==3:
        return l[0] + l[1]/60 + l[2]/3600
    if len(l)==2:
        return l[0]/60 + l[1]/3600
    if len(l)==1:
        return l[0]/3600
    return 0

def read_config():
    global CONFIG
    CONFIG = sys.argv[1]
    with open(CONFIG) as f:
        return json.load(f)


def read_activities(dl):
    activity = {}
    stack = []
    j=0
    try:
        i=0
        while i<len(dl):
            if dl[i].find(items[j])==0:
                stinfo=dl[i][len(items[j])+1:].strip()
                i+=1
                while len(re.findall("Finish", dl[i])) == 0:
                    stinfo = "{s} {d}".format(s=stinfo,d=dl[i])
                    i+=1
                stinfo_list = re.split("{i1}|{i2}|{i3}|{cst}"
                                       .format(i1=items[1], i2=items[2], i3=items[3], cst="CEST"), stinfo)
                stinfo_list = [x.strip() for x in stinfo_list]
                activity[items[0]] = stinfo_list[0]
                activity[items[1]] = get_num(stinfo_list[1])
                activity[items[2]] = get_time(stinfo_list[2])
                activity[items[3]] = "{s1} {s2}".format(s1=stinfo_list[3], s2=stinfo_list[4])
                stack.append(activity)
                activity={}
                i+=10 # nothing expected
            i+=1
        return stack
    except:
        print("Structure of your data file is corrupted!")
        raise


def find_stamp(data, stamp):
    i=0
    while i<len(data):
        if data[i][items[3]]==stamp:
            return i
        i+=1
    return -1


def update_alarms(activity, conf):
    """update 'counted' along the activity for every alarm"""
    for al in conf['alarms']:
        disdur = 1 if items[1] in al.keys() else 2
        if activity[items[0]]==al[items[0]]:
            al['counted'] += activity[items[disdur]]


def check_alarms(conf):
    """check if it's time to send some mails..."""
    for al in conf['alarms']:
        distdur = items[1] if items[1] in al else items[2]
        if al['counted']>al[distdur]:
            mailtext = "{a} \n\n Counted: {b}{j} Alarm set: {c}{j}".format(a=al['Message'],
                                                                           b=al['counted'],
                                                                           c=al[distdur],
                                                                           j=unts[distdur])
            send_email(conf['mail']['fromWh'], conf['mail']['psw'],
                       conf['mail']['toWh'], mailtext)
            al['counted'] = 0





def update_conf(conf, data):
    if 'last stamp' in conf.keys():
        i = find_stamp(data,conf['last stamp'])
        if i==-1:
            sys.exit("I haven't found last activity in your datafile, remove 'last stamp' in your config!")
        else:
            data = data[i+1:]
    for al in conf['alarms']:
        if not ('counted' in al.keys()): # no 'counted', we must count from 0
            al['counted']=0
        if not(items[1] in al.keys() or items[2] in al.keys()): # distance or duration
            sys.exit("Your alarms are setting bad!")
    for activity in data:
        update_alarms(activity, conf)
    if len(data)>0: # if something is updated, make a new stamp
        conf['last stamp']=data[-1][items[3]]
    check_alarms(conf)


def update_data(conf):
    if not ('data' in conf.keys()):
        sys.exit("Sory, there is no path to your data-file in your config")
    global SMTP, SMTPPORT, CONFIG
    SMTP = conf['mail']['smtp']
    SMTPPORT = conf['mail']['port']
    

    try:
        dataf = open(conf['data'], 'r')
    except IOError:
        print("There is a problem with your data file...")
        raise
    datalines = dataf.readlines()
    dataf.close()
    update_conf(conf, read_activities(datalines))
    with open(CONFIG, 'w') as outfile:
        json.dump(conf, outfile)



update_data(read_config())

