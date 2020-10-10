#!/usr/bin/env python

__author__ = "Jagat Jyoti Mishra"
__version__ = "1.1.0"
__maintainer__ = "Jagat Jyoti Mishra"
__email__ = "jagatjyoti0@gmail.com"


import re
import time
import os
import sys
from datetime import datetime
from kubernetes import client, config, watch
import smtplib
from email import encoders
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart

#Timestamp for logging
def prepend_timestamp():
    i = datetime.now()
    str(i)
    timestamp = i.strftime('%Y/%m/%d %H:%M:%S')
    print(timestamp)

# Fetch unhealthy pods from all namespaces
def get_unhealthy_pods():
    config.load_kube_config()
    try:
        v1 = client.CoreV1Api()
        field_selector = 'status.phase='+'Pending'
        pod_list_response = v1.list_pod_for_all_namespaces(watch=False,field_selector=field_selector)
    except ApiException as e:
        print("Exception when calling CoreV1Api->list_pod_for_all_namespaces: %s\n" % e)
    pod_dict = {}
    pod_keys = []
    pod_values = []
    for i in pod_list_response.items:
        pod_keys.append(i.metadata.name)
        pod_values.append(i.metadata.namespace)
    pod_dict = dict(zip(pod_keys, pod_values))
    return pod_dict

# Check status of single pod or all pods in namespace
def check_pod_status(query_all, pod, namespace):
    config.load_kube_config()
    field_selector='metadata.name='+pod
    pod_status_dict = {}
    pod_keys = []
    pod_values = []
    try:
        v1 = client.CoreV1Api()
        if query_all == 'True':
            pod_status_response = v1.list_namespaced_pod(namespace, watch=False)
        else:
            pod_status_response = v1.list_namespaced_pod(namespace, watch=False, field_selector=field_selector)
    except ApiException as e:
        print("Exception when calling CoreV1Api->list_namespaced_pod: %s\n" % e)
    for i in pod_status_response.items:
        # pod_status = i.status.phase
        pod_keys.append(i.metadata.name)
        pod_values.append(i.status.phase)
        res = i.spec.affinity
        var = str(res)
        if (var.find('trial') != -1):
            tenancy = 'trial'
        elif(var.find('paid') != -1):
            tenancy = 'paid'
        else:
            tenancy = 'dedicated'
    pod_status_dict = dict(zip(pod_keys, pod_values))
    return pod_status_dict, tenancy

# Pull timely event message for pod and print in pretty table format
def get_event_message(pod, namespace):
    config.load_kube_config()
    field_selector='involvedObject.name='+pod
    event_list = []
    try:
        v1 = client.CoreV1Api()
        stream = watch.Watch().stream(v1.list_namespaced_event, namespace, field_selector=field_selector, timeout_seconds=5)
        for event in stream:
            event_list.append(event['object'].message)
    except ApiException as e:
        print("Exception when calling CoreV1Api->list_namespaced_event: %s\n" % e)
    events = '<br/>'.join(event_list)
    query_all = 'False'
    pod_status, tenancy = check_pod_status(query_all, pod, namespace)
    pod_state = ' '.join(pod_status.values())
    if pod_state == ' Running':
        return
    else:
        query_all = 'True'
        other_pod_status, tenancy = check_pod_status(query_all, pod, namespace)
        for key, value in other_pod_status.items():
            other_pod_state = " : ".join([key, value])
    return events, other_pod_state, pod_state, tenancy

# Create an event series
def create_event_histogram():
    unhealthy_pod_dict = get_unhealthy_pods()
    item_count = len(unhealthy_pod_dict)
    print("Unhealthy pods: " + str(item_count))
    events_dict = {}
    other_pod_state_dict = {}
    iter = 2
    seconds = 60
    minutes = int(seconds)//60
    period = int(iter) * int(minutes)
    for x in range(iter):
        for i in range(item_count):
            events, other_pod_state, pod_state, tenancy = get_event_message(list(unhealthy_pod_dict.keys())[i], list(unhealthy_pod_dict.values())[i])
            if i not in events_dict:
                events_dict[i] = []
            events_dict[i].append(events)
            if i not in other_pod_state_dict:
                other_pod_state_dict[i] = other_pod_state
        time.sleep(seconds)
    html_row = []

    for i in range(item_count):
        #row_line = str(str(i + 1), list(unhealthy_pod_dict.keys())[i] + " " "(" + pod_state + ")", list(unhealthy_pod_dict.values())[i] + " " "(" + tenancy + ")", events_list, other_pod_state)
        sl = str(i + 1)
        pod = str(list(unhealthy_pod_dict.keys())[i] + " " "(" + pod_state + ")")
        namespace = str(list(unhealthy_pod_dict.values())[i] + " " "(" + tenancy + ")")
        events = str(events_dict[i])
        ns_pod = str(other_pod_state_dict[i])
        html_row.append("<tr><td>" + sl + "</td><td>" + pod + "</td><td>" + namespace + "</td><td>" + events + "</td><td>" + ns_pod + "</td></tr>")

    product_name = Production
    pod_count = str(item_count)
    subj = "[KUB-Monitor] Pod Status | Environment : " + product_name + "\n"

    html = """\
    <html>
      <head>
             <style>
             .header1 {
             padding: 60px;
             text-align: center;
             background: #fa4368;
             color: white;
             font-size: 40px;
             }
             .header2 {
             padding: 60px;
             text-align: center;
             background: #6e6768;
             color: white;
             font-size: 20px;
             }
             .text {
               font-family: "Trebuchet MS", Arial, Helvetica, sans-serif;
               border-collapse: collapse;
               width: 60%;
             }
        #pods {
          font-family: "Trebuchet MS", Arial, Helvetica, sans-serif;
          border-collapse: collapse;
          width: 100%;
        }
        #pods h2 {
        background-color: red;
        color: #ffffff;
        padding: 15px;
        }

        #pods td, #pods th {
          border: 1px solid #ddd;
          padding: 8px;
        }

        #pods tr:nth-child(even){background-color: #f2f2f2;}

        #pods tr:hover {background-color: #ddd;}

        #pods th {
          padding-top: 12px;
          padding-bottom: 12px;
          text-align: left;
          background-color: #33b5e5;
          color: white;
        }
        </style>
      </head>
      <body>
           <div class="header1"><center>  ALERT  </center></div><br>
            <p class="text">Unhealthy pods: <b>""" +str(pod_count)+ """</b><br>
            Environment: """ +str(product_name)+ """<br>
            Frequency: Pulled every """ +str(minutes)+ """ minutes for  """ +str(iter)+ """ Iterations <br>
            Period: Status of pod for last """ +str(period)+ """ minutes <br><br></p>
        <div class="header2"><center>Details as below</center></div>
        <table id="pods">
    <tr>
    <th>Sl</th>
    <th>Pod</th>
    <th>Namespace</th>
    <th>Events</th>
    <th>Namespaced Pod</th>
    </tr>
    """ + str(html_row) + """
    </table>
      </body>
    </html>
    """
    if item_count == 0:
        print("No unhealthy pods reported. Mailing action suppressed")
        sys.exit(0)
    else:
        mail_notification(product_name, html, subj)

# Send notification to recipients
def mail_notification(product_name, html, subj):
    sender = 'jagatjyoti0@gmail.com'
    recipients = ['jagatjyoti0@gmail.com']
    mymail = MIMEMultipart()
    mymail['To'] = ','.join(recipients)
    mymail['From'] = sender
    mymail['Subject'] = subj
    # mytext = text
    # mymail.attach(
    # MIMEText(text, 'plain'))
    mymail.attach(
    MIMEText(html, 'html'))

    message = mymail.as_string()

    try:
        smtpObj = smtplib.SMTP('localhost')
        smtpObj.sendmail(sender, recipients, message)
        smtpObj.close()
        print("Notification sent to intended recipients")
    except smtplib.SMTPException as e:
       print(e)
       print("Failed sending notification")

#Main
if __name__ == '__main__':
    prepend_timestamp()
    create_event_histogram()
    print("Done")
