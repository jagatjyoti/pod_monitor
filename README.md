# pod_monitor

Pod monitor is a Python utility for getting event histogram of all the unhealthy pods over a certain period of time inside your Kubernetes cluster.

## Description

The utility is capable of providing data about unhealthy pods in your cluster. By default, it watches the pods for 1 hour (can be adjusted) before mailing the events in a nice HTML format. It also tells you the state of other pods in the same namespace where it has found an unhealthy pod. This is based on the [ Python Kubernetes client ](https://github.com/kubernetes-client/python) which does API calls to the cluster and above link carries instructions about downloading it.  

## Running it

It can be run upon demand or best way is to just put it under cron so that it sends hourly mail notification about the pods' status. Running this requires no additional option.

```
$ python pod_monitor.py
```
### Info

The goal of this utility is to provide a concrete idea about the pod's health over a period of time as quite often it's noticed that pods keep on getting restarted.
