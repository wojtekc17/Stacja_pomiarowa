import serial
import time
from datetime import datetime

import sys
from tkinter import *
import tkinter as tk

import MySQLdb

import schedule

import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from pandas import DataFrame
import pandas as pd
import numpy as np

import gc

def GraphPlot(table,y0,y1,ylabel,figure,canv,time_hour):
    con=MySQLdb.connect("localhost","pi","root","sds018_data")
    cur=con.cursor()
    data_x=[]
    data_y=[]
    try:
        cur.execute("SELECT measurement FROM %s WHERE (date <= NOW() AND date >= NOW() - INTERVAL %d HOUR)" %(table,time_hour))
        result_y=cur.fetchall()
        for i in result_y:
            data_y.append(i[0])
          #  data_y.insert(0,i[0])
     #   for i in data_y:
     #      print(i)
        form_data="DATE_FORMAT(date,'%Y.%m.%d %H:%i:%s')"
        cur.execute("SELECT %s FROM %s WHERE (date <= NOW() AND date >= NOW() - INTERVAL %d HOUR)" %(form_data,table,time_hour))
       # cur.execute("SELECT %s FROM %s ORDER BY id DESC LIMIT 1440" %(form_data,table))
        result_x=cur.fetchall()
        for i in result_x:
            data_x.append(i[0])
           # data_x.insert(0,i[0])
   #     for i in data_x:
    #        print(i)     
   #     print(len(data_x), len(data_y))
        con.commit()
    except MySQLdb.Error:
        print ("AN error has occurred.")
    finally:
        cur.close()
        con.close()
    Plot(data_x,data_y,y0,y1,ylabel,figure,canv)
    del data_x
    del data_y
    del result_x
    del result_y
    gc.collect()
	
    
def Plot(data_x,data_y,y0,y1,ylabel,figure,canv):    
    Dataa = {'Data': data_x,'Mes': data_y}
    df = pd.DataFrame(Dataa,columns=['Data','Mes'])
    df.Data=df.Data.astype('str')
    df.Mes=df.Mes.astype('float')
    df = df[['Data', 'Mes']].groupby('Data').sum()
  #  print(df.to_string())
    figure.clear()
    y_mask_y = np.ma.masked_less_equal(data_y,y0)
    y_mask_r = np.ma.masked_less_equal(data_y,y1) 
    df.plot(kind='line',legend=False,color='g',ax=figure,linewidth=1, fontsize=10)
    figure.plot(y_mask_y, color='darkorange', linewidth=1)
    figure.plot(y_mask_r, color='red', linewidth=1)
    figure.axhline(y0, color='orange', linestyle='--')
    figure.axhline(y1, color='r', linestyle='--')
    l1=('0-%d stan dobry' %y0)
    l2=('%d-%d stan umiarkowany' %(y0,y1))
    l3=('%d+ stan zły' %y1)
    figure.legend((l1,l2,l3),loc='upper left')
    figure.grid(True)
    figure.set_xlabel('Data[Y.M.D H:M:S] ')
    figure.set_ylabel('Ilość %s w powietrzu[ug/$m^3$]' %ylabel)
    figure.set_title('Pomiar %s' %ylabel)
    canv.draw()
    del df
    del y_mask_r
    del y_mask_y
    gc.collect()

def ClearAllTables():
    con=MySQLdb.connect("localhost","pi","root","sds018_data")
    cur=con.cursor()
    try:
        cur.execute("TRUNCATE TABLE TablesPM2_5")
        cur.execute("TRUNCATE TABLE TablesPM10")
        cur.execute("TRUNCATE TABLE Tables_1min")
        cur.execute("TRUNCATE TABLE Tables_1h")
        cur.execute("TRUNCATE TABLE Tables_1day")
        con.commit()
    except MySQLdb.Error:
        print ("AN error has occurred.")
    finally:
        cur.close()
        con.close()
    return 0

def ParamSaveTablesPM2_5andPM10(PM2_5,PM10):
    con=MySQLdb.connect("localhost","pi","root","sds018_data")
    cur=con.cursor()
    try:
        params=[PM2_5]
        cur.execute("INSERT INTO TablesPM2_5(id,measurement,date) VALUE (NULL,%s,NOW())",params)
        params=[PM10]
        cur.execute("INSERT INTO TablesPM10(id,measurement,date) VALUE (NULL,%s,NOW())",params)
        con.commit()
    except MySQLdb.Error:
        print ("AN error has occurred.")
    finally:
        cur.close()
        con.close()
    return 0

def RedUART(ser):
    ch=ser.read()
    time.sleep(0.03)
    data=ser.inWaiting()
    ch+=ser.read(data)
    return ch

def CalculatePM2_5(message_uart):
    PM2_5=((message_uart[3]*256)+message_uart[2])/10 #ug/m^3
    return PM2_5

def CalculatePM10(message_uart):
    PM10=((message_uart[5]*256)+message_uart[4])/10  #ug/m^3
    return PM10

def Checksum(message_uart):
    checksumm=message_uart[2]+message_uart[3]+message_uart[4]+message_uart[5]+message_uart[6]+message_uart[7]
    while checksumm>=256:
        checksumm=checksumm-256
    return checksumm

def VerificationMessageUart():
    port= "/dev/ttyS0"
    ser = serial.Serial(port,baudrate=9600)
    while True:
        message_uart=RedUART(ser)
        #print(message_uart)
        if len(message_uart)==10:
            checksumm=Checksum(message_uart)
            #print(checksumm)
            #print(message_uart[8])
            if message_uart[8]==checksumm:
                PM2_5=CalculatePM2_5(message_uart)
                PM10=CalculatePM10(message_uart)
                ParamSaveTablesPM2_5andPM10(PM2_5,PM10)
                #labPM10.configure(text=PM10)   
                #labPM25.configure(text=PM2_5)
                if PM2_5<=13 and PM10<=20:
                    labCOMUNICAT.configure(text="Jakość powietrza jest bardzo dobra(PM2.5=%d, PM10=%d)!" %(PM2_5,PM10),fg="lime")
                elif PM2_5<=35 and PM10<=50:
                    labCOMUNICAT.configure(text="Jakość powietrza jest dobra(PM2.5=%d, PM10=%d)" %(PM2_5,PM10),fg="green" ) 
                elif PM2_5<=55 and PM10<=80:
                    labCOMUNICAT.configure(text="Jakość powietrza jest umiarkowana(PM2.5=%d, PM10=%d)" %(PM2_5,PM10),fg="gold")
                elif PM2_5<=75 and PM10<=110:
                    labCOMUNICAT.configure(text="Jakość powietrza jest dostateczna(PM2.5=%d, PM10=%d)" %(PM2_5,PM10),fg="darkorange")
                elif PM2_5<=110 and PM10<=150:
                    labCOMUNICAT.configure(text="Jakość powietrza jest zła(PM2.5=%d,PM10=%d)" %(PM2_5,PM10),fg="red")
                else: 
                    labCOMUNICAT.configure(text="Jakość powietrza jest bardzo zła(PM2.5=%d,PM10=%d)!!!" %(PM2_5,PM10),fg="darkred")
                break

def Clock():
    root.after(1000,Clock)
    now=datetime.now()
    dt_now=now.strftime("%H:%M  %d.%m.%Y ")
    #print("now=",dt_now)
    labCLOCK.configure(text=dt_now)

def CloseWindow():
    root.destroy()

def Tick():
    global variable
    root.after(60000,Tick)
    VerificationMessageUart()
    GraphPlot("TablesPM2_5",35,75,"PM2.5",ax1,canv1,variable)
    GraphPlot("TablesPM10",50,110,"PM10",ax2,canv2,variable)
    
def main():
    print ("starting")
    #ClearAllTables()
    Clock()
    Tick()

variable=1
def ChangeVariable(value):
    global variable
    variable=value
    GraphPlot("TablesPM2_5",35,75,"PM2.5",ax1,canv1,variable)
    GraphPlot("TablesPM10",50,110,"PM10",ax2,canv2,variable)
    
root=Tk()
root.configure(background='white')
root.overrideredirect(-1)
root.geometry('1920x1080')

frame1=Frame(root,bg="white")
frame1.grid(row=0,column=0,sticky="WE")

frame2=Frame(root,bg="white")
frame2.grid(row=1,column=0,sticky="WE")

#frame3=Frame(root,bg="white")
#frame3.grid(row=2,column=0,sticky="WE")

labTITLE=Label(frame1,font=('times',50,'bold'),bg='white')
labTITLE.grid(row=0,column=0,in_=frame1)
labTITLE.configure(text='System do pomiaru zapylenia powietrza')
#labPM10=Label(root,font=("times",25,"bold"),bg="white")
#labPM10.grid(row=1,column=0)
#labPM10.configure(text="xDDDDDDDDDDDD")

labCOMUNICAT=Label(frame1,font=('times',40,'bold'),bg='white')
labCOMUNICAT.grid(row=3,column=0,in_=frame1)

labCLOCK=Label(frame2,font=('times',10,'bold'),bg='white')
labCLOCK.grid(row=0,column=5,in_=frame2,padx=1035,pady=10)

#buttonTABLE=Button(frame2,text="Table",command=Table)
#buttonTABLE.grid(row=0,column=1,in_=frame2,padx=10,pady=70)

buttonQUIT=Button(frame2,text="Quit",command=CloseWindow)
buttonQUIT.grid(row=0,column=0,in_=frame2,padx=10,pady=10)

button1HOUR=Button(frame2,text="Wykres ostatniej godziny",command=lambda: ChangeVariable(1))
button1HOUR.grid(row=0,column=1,in_=frame2,padx=5,pady=10)

button1DAY=Button(frame2,text="Wykres 1 dzień",command=lambda: ChangeVariable(24))
button1DAY.grid(row=0,column=2,in_=frame2,padx=5,pady=10)

button7DAY=Button(frame2,text="Wykres 7 dni",command=lambda: ChangeVariable(168))
button7DAY.grid(row=0,column=3,in_=frame2,padx=5,pady=10)

button31DAY=Button(frame2,text="Wykres 30 dni",command=lambda: ChangeVariable(720))
button31DAY.grid(row=0,column=4,in_=frame2,padx=5,pady=10)


figure1 = Figure(figsize=(18.2,4), dpi=100)
ax1 = figure1.add_subplot(111)
canv1 = FigureCanvasTkAgg(figure1, frame1)
canv1.get_tk_widget().grid(row=1,column=0,in_=frame1,padx=0,pady=0)

figure2 = Figure(figsize=(18.2,4), dpi=100)
ax2 = figure2.add_subplot(111)
canv2 = FigureCanvasTkAgg(figure2, frame1)
canv2.get_tk_widget().grid(row=2,column=0,in_=frame1,padx=0,pady=0)


main()
root.mainloop()

