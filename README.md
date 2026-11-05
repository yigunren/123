# 基于 MobileNetV2 的番茄叶片病害识别

课程设计项目：使用迁移学习完成 6 类番茄叶片病害分类，包含数据准备、训练、评估、单张预测和 Grad-CAM 可视化。

## 1. 项目结果

- 数据集：PlantVillage 番茄 6 类，每类 500 张，共 3000 张
- 划分：训练 2100 / 验证 450 / 测试 450
- 模型：MobileNetV2（ImageNet 预训练）+ 两阶段迁移学习
- 测试准确率：**89.11%**
- Top-3 准确率：**99.33%**
- 宏平均 F1：**0.8912**
- 参数量：约 **2.27 M**
- 训练环境：CPU、TensorFlow 2.21.0、Keras 3.14.1

## 2. 目录结构

```text
data/
  plantvillage_subset/     6 类番茄叶片图片
  splits.csv               训练/验证/测试划分
src/
  config.py                路径、类别、超参数
  prepare_data.py          扫描数据并分层切分
  eda.py                   类别分布与样例图
  train.py                 训练、微调、评估、绘图
  predict.py               单张图片预测
  gradcam.py               Grad-CAM 可视化
  make_diagram.py          横向模型结构图（PPT 用）
  make_diagram_vertical.py 竖向模型结构图
  make_report.py           生成课程设计报告 DOCX
outputs/
  models/                  tomato_mobilenetv2.h5
  figures/                 训练曲线、混淆矩阵、预测样例、Grad-CAM
  metrics/                 metrics.json、classification_report.txt
report/
  基于MobileNetV2的番茄叶片病害识别-课程设计报告.docx
  基于MobileNetV2的番茄叶片病害识别-课程设计报告.pdf
  基于MobileNetV2的番茄叶片病害识别-答辩PPT.pptx
```

## 3. 运行方式

```bash
pip install -r requirements.txt

# 1) 生成训练/验证/测试划分
python src/prepare_data.py

# 2) 训练（CPU 即可，约十余分钟）
python src/train.py --stage1-epochs 12 --stage2-epochs 6

# 3) 单张预测
python src/predict.py <图片路径>

# 4) Grad-CAM 六类样例
python src/gradcam.py --grid
```

## 4. 数据说明

数据来自公开的 PlantVillage 数据集，本文从 `color` 子集中选取番茄的 6 个类别，每类 500 张：

- 番茄细菌性斑点病
- 番茄早疫病
- 番茄晚疫病
- 番茄叶霉病
- 番茄斑枯病
- 番茄健康叶片

原始图像为 256×256 RGB，训练时统一缩放到 160×160。

## 5. 结果文件

- `outputs/metrics/metrics.json`：总体指标
- `outputs/metrics/classification_report.txt`：分类别指标
- `outputs/figures/training_curves.png`：训练曲线
- `outputs/figures/confusion_matrix.png`：混淆矩阵
- `outputs/figures/sample_predictions.png`：预测样例
- `outputs/figures/gradcam_grid.png`：Grad-CAM
- `outputs/models/tomato_mobilenetv2.h5`：最终模型
