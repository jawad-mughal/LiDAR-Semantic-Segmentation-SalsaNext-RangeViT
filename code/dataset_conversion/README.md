Dataset Conversion Utilities
Overview

This folder contains custom utilities developed for converting Ouster LiDAR measurements recorded in ROS bag format into SemanticKITTI-compatible binary point cloud files.

These utilities were developed as part of a LiDAR Semantic Segmentation project using SalsaNext and RangeViT for autonomous driving applications.

Script
rosbag_to_semantickitti_converter.py

Converts ROS bag recordings containing PointCloud2 messages into SemanticKITTI-compatible .bin files.

Main Features:
Reads ROS bag files
Supports PointCloud2 messages
Extracts XYZ and remission/intensity information
Filters invalid and padded points
Generates SemanticKITTI sequence structure
Creates timestamp files for each sequence
Produces binary files compatible with SalsaNext and RangeViT


Technologies
Python
ROS Bags
PointCloud2
Ouster LiDAR
SemanticKITTI
NumPy
Applications
LiDAR Semantic Segmentation
Autonomous Driving
Deep Learning Pipelines
Point Cloud Processing
Dataset Preparation
Author

Muhammad Jawad

M.Sc. Geoinformatics

Leibniz University Hannover
