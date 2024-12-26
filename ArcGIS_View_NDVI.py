#!/usr/bin/python
# -*- coding: utf-8 -*-

import arcpy
from arcpy import env
import os
import time
import arcpy.management
import arcpy.stats
from arcpy.sa import *

time_start = time.time()
# 打印现在的年月日时分秒时间
print('start time:'+time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))

# 设置工作空间
env.workspace = r" ArcGIS的工作空间路径"

# 输入NDVI数据路径
ndvi_raster = r" NDVI栅格数据路径"

# 输入点 shapefile 路径
point_shapefile=r"在DSM上取得Z值的视域点集"

# 输入的缓冲区和视域结果的目录
buffer_dir=r"缓冲区中间路径文件夹"
viewshed_shp_dir=r"视域范围路径文件夹"
# 输出的NDVI统计分区结果表的文件夹路径
NDVI_tmp=r"NDVI中间表文件夹路径"

# 设置分析环境
arcpy.env.overwriteOutput = True

# 添加字段
arcpy.management.AddField(point_shapefile, "BuMe", "DOUBLE")
arcpy.management.AddField(point_shapefile, "BuSu", "DOUBLE")
arcpy.management.AddField(point_shapefile, "ViMe", "DOUBLE")
arcpy.management.AddField(point_shapefile, "ViSu", "DOUBLE")

i=0  #计数print用
# 获取点 shapefile 中的所有点
with arcpy.da.SearchCursor(point_shapefile, ["id", "SHAPE@","FID"]) as points:
    # 只计算第4462个点和后面的点
    for point in points:
        point_fid = point[0]
        point_geometry = point[1]
        if point[2]>4461 and point[2]<4474:   # 若中途崩溃或不可抗原因程序终止，断点续跑
        # 在每次循环开始时检查并删除视域结果文件夹中的现有文件
            # for file in os.listdir(output_viewshed_dir):
            #     file_path = os.path.join(output_viewshed_dir, file)
            #     if os.path.isfile(file_path):
            #         os.remove(file_path)

            # 循环搜索buffer文件夹中的shp文件
            for file in os.listdir(buffer_dir):
                if file.endswith(".shp"):
                    file_path = os.path.join(buffer_dir, file)
                    # 将文件名中的点id提取出来
                    file_id = file_path.split("_")[1].split(".")[0]
                    if file_id == str(point_fid):
                        try:
                            print(str(file_id)+" "+str(point_fid))
                            # 使用NDVI进行分区统计到表格 模式用平均
                            zonal_buffer_mean = ZonalStatisticsAsTable(
                                # 输入的文件为buffer的shp文件
                                in_zone_data=file_path,
                                zone_field="FID",
                                in_value_raster=ndvi_raster,
                                out_table=os.path.join(NDVI_tmp, "NDVI_buffer_mean_" + str(point_fid) + ".dbf"),
                                statistics_type="MEAN"
                            )
                            zonal_buffer_sum = ZonalStatisticsAsTable(
                                in_zone_data=file_path,
                                zone_field="FID",
                                in_value_raster=ndvi_raster,
                                out_table=os.path.join(NDVI_tmp, "NDVI_buffer_sum_" + str(point_fid) + ".dbf"),
                                statistics_type="SUM"
                            )
                        except:
                            print("有错误计算，赋值0并跳过")
                            # 直接赋值为0
                            with arcpy.da.UpdateCursor(point_shapefile, ["id", "BuMe", "BuSu"]) as update_cursor:
                                for update_row in update_cursor:
                                    if update_row[0] == point_fid:
                                        update_row[1] = 0
                                        update_row[2] = 0
                                        update_cursor.updateRow(update_row)
                        
                        with arcpy.da.SearchCursor(zonal_buffer_mean, ["MEAN"]) as cursor:
                                for row in cursor:
                                    with arcpy.da.UpdateCursor(point_shapefile, ["id", "BuMe"]) as update_cursor:
                                        for update_row in update_cursor:
                                            if update_row[0] == point_fid:
                                                update_row[1] = row[0]
                                                update_cursor.updateRow(update_row)
                            
                        with arcpy.da.SearchCursor(zonal_buffer_sum, ["SUM"]) as cursor:
                                for row in cursor:
                                    with arcpy.da.UpdateCursor(point_shapefile, ["id", "BuSu"]) as update_cursor:
                                        for update_row in update_cursor:
                                            if update_row[0] == point_fid:
                                                update_row[1] = row[0]
                                                update_cursor.updateRow(update_row)

            # 视域要求MEAN和SUM
            # 循环搜索视域文件夹中的文件
            for file_Bu in os.listdir(viewshed_shp_dir):
                if file_Bu.endswith(".shp"):
                    file_path_Bu = os.path.join(viewshed_shp_dir, file_Bu)         
                    # 将文件名中的点id提取出来
                    file_id_Bu = file_Bu.split("_")[2].split(".")[0]
                    if file_id_Bu == str(point_fid):
                        print(str(file_id_Bu)+" "+str(point_fid))
                        try:
                            # 使用NDVI进行分区统计到表格 模式用平均和求和
                            zonal_viewshed_mean = ZonalStatisticsAsTable(
                                in_zone_data=file_path_Bu,
                                zone_field="FID",
                                in_value_raster=ndvi_raster,
                                out_table=os.path.join(NDVI_tmp, "NDVI_viewshed_mean_" + str(point_fid) + ".dbf"),
                                statistics_type="MEAN"
                            )
                            zonal_viewshed_sum = ZonalStatisticsAsTable(
                                in_zone_data=file_path_Bu,
                                zone_field="FID",
                                in_value_raster=ndvi_raster,
                                out_table=os.path.join(NDVI_tmp, "NDVI_viewshed_sum_" + str(point_fid) + ".dbf"),
                                statistics_type="SUM"
                            )
                        except:
                            print("有错误计算，赋值0并跳过")
                            # 直接赋值为0
                            with arcpy.da.UpdateCursor(point_shapefile, ["id", "ViMe", "ViSu"]) as update_cursor:
                                for update_row in update_cursor:
                                    if update_row[0] == point_fid:
                                        update_row[1] = 0
                                        update_row[2] = 0
                                        update_cursor.updateRow(update_row)
                        
                        with arcpy.da.SearchCursor(zonal_viewshed_mean, ["MEAN"]) as cursor:
                            for row in cursor:
                                with arcpy.da.UpdateCursor(point_shapefile, ["id", "ViMe"]) as update_cursor:
                                    for update_row in update_cursor:
                                        if update_row[0] == point_fid:
                                            update_row[1] = row[0]
                                            update_cursor.updateRow(update_row)
                        with arcpy.da.SearchCursor(zonal_viewshed_sum, ["SUM"]) as cursor:
                            for row in cursor:
                                with arcpy.da.UpdateCursor(point_shapefile, ["id", "ViSu"]) as update_cursor:
                                    for update_row in update_cursor:
                                        if update_row[0] == point_fid:
                                            update_row[1] = row[0]
                                            update_cursor.updateRow(update_row)
            # 计数器
            i=i+1
            
            # 打印每次运行的状况
            tmp=r"Buffer and viewshed Caluculation Completed: point id " + str(point_fid)+" No. "+str(i)+" point - "+time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            print(tmp)

    # 释放内存
    del zonal_buffer_mean
    del zonal_buffer_sum
    del zonal_viewshed_mean
    del zonal_viewshed_sum

time_end = time.time()
print("共计用时 " + str(time_end - time_start)+' 秒')
print('end time:'+time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
print("所有视域分析完成")
