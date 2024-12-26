#!/usr/bin/python
# -*- coding: utf-8 -*-

import arcpy
from arcpy import env
import os
import time
from arcpy.sa import *

time_start = time.time()
print('start time:' + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))

# 设置工作空间
env.workspace = r"ArcGIS的工作空间路径"

# 输入数据路径
dsm_raster = r"DSM数据路径
# 视域计算点
point_shapefile = r"在DSM上取得Z值的视域点集"
ndvi_raster = r"NDVI栅格数据路径"
green_forest_raster = r"绿色森林波段数据路径"
green_grass_raster = r"绿色草地波段数据路径"
blue_river_raster = r"蓝色河流波段数据路径"
blue_pool_raster = r"蓝色池塘波段数据路径"

# 输出文件目录
output_buffer_dir = r"缓冲区中间路径文件夹"
output_viewshed_dir = r"蓝绿波段中间数据表路径文件夹"
output_viewshed_shp_dir = r"视域范围路径文件夹"
output_ndvi_dir = r"NDVI中间数据表路径文件夹"
buffer_distance = "1000 Meters" # 设置缓冲区的范围
dissolve_field = "FID"

# 环境设置
arcpy.env.overwriteOutput = True

# 创建输出目录
if not os.path.exists(output_buffer_dir):
    os.makedirs(output_buffer_dir)
if not os.path.exists(output_viewshed_dir):
    os.makedirs(output_viewshed_dir)
if not os.path.exists(output_viewshed_shp_dir):
    os.makedirs(output_viewshed_shp_dir)
if not os.path.exists(output_ndvi_dir):
    os.makedirs(output_ndvi_dir)

# 添加字段
fields_to_add = ["view_area", "forest", "grass", "river", "pool", "BuMe", "BuSu", "ViMe", "ViSu"]
for field in fields_to_add:
    arcpy.management.AddField(point_shapefile, field, "DOUBLE")

i = 0

# 获取点 shapefile 中的所有点
with arcpy.da.SearchCursor(point_shapefile, ["id", "SHAPE@", "FID"]) as points:
    for point in points:
        point_fid, point_geometry = point[0], point[1]

        # 输出路径
        output_buffer = os.path.join(output_buffer_dir, r"buffer_" + str(point_fid) + ".shp")
        output_viewshed = os.path.join(output_viewshed_dir, r"viewshed_" + str(point_fid) + ".tif")
        output_viewshed_shp = os.path.join(output_viewshed_shp_dir, r"viewshed_" + str(point_fid) + ".shp")

        # 创建缓冲区
        arcpy.Buffer_analysis(point_geometry, output_buffer, buffer_distance)

        # 设置分析范围为缓冲区
        arcpy.env.mask = output_buffer

        # 进行视域分析
        arcpy.Viewshed2_3d(dsm_raster, point_geometry, output_viewshed,
                            analysis_type="FREQUENCY", refractivity_coefficient=0.13,
                            analysis_method="PERIMETER_SIGHTLINES")
        
        # 转换栅格为矢量
        arcpy.RasterToPolygon_conversion(output_viewshed, output_viewshed_shp, "NO_SIMPLIFY", "VALUE")
        arcpy.management.Delete(output_viewshed)  # 删除中间结果

        i += 1
        print(r"Visual field analysis completed: point id "+str(point_fid)+" No. "+str(i)+" point - " +
              time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))

        # 合并shp文件
        output_viewshed_shp_merged = os.path.join(output_viewshed_shp_dir, r"viewsheds_merged_"+str(point_fid)+".shp")
        arcpy.Dissolve_management(output_viewshed_shp, output_viewshed_shp_merged, dissolve_field)

        # 计算面积并更新字段
        arcpy.management.AddField(output_viewshed_shp_merged, "Area", "DOUBLE")
        arcpy.management.CalculateField(output_buffer, "Area", "!SHAPE.area!", "PYTHON_9.3")
        arcpy.management.CalculateField(output_viewshed_shp_merged, "Area", "!SHAPE.area!", "PYTHON_9.3")

        buffer_area = 0
        viewshed_area = 0

        with arcpy.da.SearchCursor(output_buffer, ["Area"]) as cursor:
            for row in cursor:
                buffer_area = row[0]

        with arcpy.da.SearchCursor(output_viewshed_shp_merged, ["Area"]) as cursor:
            for row in cursor:
                viewshed_area = row[0]

        # 更新point_shapefile的字段
        with arcpy.da.UpdateCursor(point_shapefile, ["id", "view_area"]) as cursor:
            for row in cursor:
                if row[0] == point_fid:
                    row[1] = viewshed_area
                    cursor.updateRow(row)

        # 删除未合并的shp
        arcpy.management.Delete(output_viewshed_shp)

        # 进行区域统计
        raster_stats = [(green_forest_raster, "forest"), (green_grass_raster, "grass"),
                        (blue_river_raster, "river"), (blue_pool_raster, "pool")]
        for raster, field_name in raster_stats:
            zonal_table = ZonalStatisticsAsTable(output_viewshed_shp_merged, "FID", raster,
                                                  os.path.join(output_viewshed_dir, str(field_name)+"_table_"+str(point_fid)+".dbf"),
                                                  statistics_type="SUM")
            with arcpy.da.SearchCursor(zonal_table, ["AREA"]) as cursor:
                for row in cursor:
                    with arcpy.da.UpdateCursor(point_shapefile, ["id", field_name]) as update_cursor:
                        for update_row in update_cursor:
                            if update_row[0] == point_fid:
                                update_row[1] = row[0]
                                update_cursor.updateRow(update_row)

        # 计算NDVI
        for zone_data, zone_field, output_prefix in [(output_buffer, "Bu", "NDVI_buffer"), (output_viewshed_shp_merged, "Vi", "NDVI_viewshed")]:
            try:
                zonal_mean = ZonalStatisticsAsTable(zone_data, "FID", ndvi_raster,
                                                      os.path.join(output_ndvi_dir,str(output_prefix)+"_mean_"+str(point_fid)+".dbf"),
                                                      statistics_type="MEAN")
                zonal_sum = ZonalStatisticsAsTable(zone_data, "FID", ndvi_raster,
                                                    os.path.join(output_ndvi_dir, str(output_prefix)+"_sum_"+str(point_fid)+".dbf"),
                                                    statistics_type="SUM")
                for stat_type in ["MEAN", "SUM"]:
                    with arcpy.da.SearchCursor(zonal_mean if stat_type == "MEAN" else zonal_sum, [stat_type]) as cursor:
                        for row in cursor:
                            with arcpy.da.UpdateCursor(point_shapefile, ["id", str(zone_field)+"Me" if stat_type == "MEAN" else str(zone_field)+"Su"]) as update_cursor:
                                for update_row in update_cursor:
                                    if update_row[0] == point_fid:
                                        update_row[1] = row[0]
                                        update_cursor.updateRow(update_row)
            except Exception as e:
                print(r"计算 "+str(zone_field)+" 分区的NDVI出错: "+str(e))
                with arcpy.da.UpdateCursor(point_shapefile, ["id", str(zone_field)+"Me", str(zone_field)+"Su"]) as cursor:
                    for row in cursor:
                        if row[0] == point_fid:
                            row[1], row[2] = 0, 0
                            cursor.updateRow(row)
        print(r"NDVI analysis completed: point id "+str(point_fid)+" No. "+str(i)+" point - " +
              time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))

time_end = time.time()
print("共计用时 " + str(time_end - time_start) + ' 秒')
print('end time:' + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
print("所有视域分析完成")
