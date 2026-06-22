# LiDAR Semantic Segmentation using SalsaNext and RangeViT

![SalsaNext Architecture](images/salsanext_architecture.png)

LiDAR Semantic Segmentation using SalsaNext and RangeViT
Overview

This project investigates semantic segmentation of 3D LiDAR point clouds using state-of-the-art deep learning architectures, SalsaNext and RangeViT. The work was conducted as part of the Project Seminar at Leibniz University Hannover.

The objective was to evaluate the generalization capabilities of pretrained models on real-world Ouster LiDAR data and improve performance through transfer learning and domain adaptation techniques.

Project Goals
Convert raw Ouster LiDAR measurements into SemanticKITTI-compatible format
Generate range-image representations from point clouds
Evaluate pretrained SalsaNext and RangeViT models
Perform manual point cloud annotation
Fine-tune pretrained networks on custom data
Compare CNN-based and Vision Transformer-based approaches
Analyze semantic segmentation performance for autonomous driving applications

## Key Contributions

- Adapted SalsaNext and RangeViT to custom Ouster LiDAR datasets
- Converted raw LiDAR scans to SemanticKITTI format
- Implemented transfer learning and fine-tuning workflows
- Performed manual point cloud annotation
- Evaluated CNN and Vision Transformer architectures
- Investigated domain adaptation challenges for autonomous driving

  
Technologies
Python
PyTorch
LiDAR Point Clouds
SemanticKITTI
SalsaNext
RangeViT
Deep Learning
Computer Vision
Transfer Learning
Autonomous Driving
Repository Structure

docs/ – Final report

presentations/ – Project presentations

images/ – Results and visualizations

code/ – Supporting scripts and utilities

Author

Muhammad Jawad

M.Sc. Geoinformatics

Leibniz University Hannover
