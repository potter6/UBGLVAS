#!/usr/bin/python
# -*- coding: utf-8 -*-

import multiprocessing
import os

def run_script(script_name):
    os.system("python "+str(script_name))

if __name__ == "__main__":
# 定位到 d:\Program Files (x86)\ArcGIS 10.8\python27\ArcGIS10.8
# 即用户自身的ArcGIS10.8安装的文件夹，升级后的ArcGIS Pro类似，把py文件放入该文件夹
    os.chdir(r"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3")
    scripts = ["ArcGIS_View_Calculate1.py", 
               "ArcGIS_View_Calculate2.py", 
"ArcGIS_View_Calculate3.py",
…]

    processes = []
    for script in scripts:
        process = multiprocessing.Process(target=run_script, args=(script,))
        process.start()
        processes.append(process)

    for process in processes:
        process.join()

