#!/usr/bin/python3

import sys
import signal
import pickle
import time, math
import logging
from socket import gethostbyname
from statistics import mean, stdev
from scapy.all import *

logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

ECHO_REQUEST_TYPE = 8
TTL_EXPIRED_IN_TRANSIT = 11

def get_rtt(target, ttl):
    icmp = ICMP()
    icmp.type= ECHO_REQUEST_TYPE
    pkt = IP(dst=target, ttl=ttl)/icmp/"X"
    startTime = time.time()
    response = sr1(pkt, verbose=0, timeout=2)
    endTime = time.time()
    rttTotal = (endTime - startTime) * 1000
    rttDec, rtt = math.modf(rttTotal)
    return response, rtt

def explore_hops(target_txt):
    target = gethostbyname(target_txt)
    timeToLive = 1
    rtts = []
    hops = []
    ttls = []
    while timeToLive < 35:
        response, rtt = get_rtt(target, timeToLive)
        print("TTL=", timeToLive)
        if not response is None:
            rtts.append(rtt)
            hops.append(response[IP].src)
            ttls.append(timeToLive)
            if response[ICMP].type == TTL_EXPIRED_IN_TRANSIT:
                print("El RTT para esta IP", response[IP].src, "fue de:", rtt)
            else:
                print("Llegaste hasta", target_txt, "que tiene la IP:", response[IP].src)
                break
        timeToLive += 1
    if timeToLive == 35:
        print("ERROR: El host" + target + "es inalcanzable")
    return rtts, hops, ttls


def main(target, reps):
    timeToLive = 1

    rtts, hops, ttls = explore_hops(target)

    # Mido ZRTT
    avg_rtts = rtts
    total_rtts = [rtts]
    rtts = []

    for rep in range(1, reps):
        print ("Ejecutando repeticion", str(rep), "...")
        for i in range(0, len(hops)):
            response, rtt = get_rtt(target, ttls[i])
            if hops[i] != response[IP].src:
                print("WARNING: La ruta parece haber cambiado")
                print("Quería llegar a", hops[i], "pero me respondió", response[IP].src)
            rtts.append(rtt)
            avg_rtts[i] += rtt
        total_rtts.append(rtts)

    # Promedio
    for i in range(0, len(avg_rtts)):
        avg_rtts[i] /= reps

    zrtts = []
    for avg_rtt in avg_rtts:
        zrtt = (avg_rtt - mean(avg_rtts)) / stdev(avg_rtts)
        zrtts.append(zrtt)

    return zrtts, avg_rtts, hops


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("ERROR: Debe especificar una URL o IP de destino")
        exit()
    if len(sys.argv) < 3:
        reps = 1
    else:
        reps = int(sys.argv[2])

    zrtts, avg_rtts, hops = main(sys.argv[1], reps)

    for i, hop in enumerate(hops):
        print(hop)
        print("\tZRTT:", zrtts[i])
        print("\tAVG RTT:", avg_rtts[i])
          