"""扫描 6 类番茄叶片数据，做分层 70/15/15 切分，输出 splits.csv。"""
from pathlib import Path
import sys

import pandas as pd
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DATA_DIR, SPLIT_CSV, CLASS_NAMES_ZH, SEED


def main():
    """扫描 data/plantvillage_subset 下的类别文件夹，生成带 split 列的 CSV。

    目录约定：每个类别一个文件夹，文件夹名必须是 config.CLASS_NAMES_ZH 的键。
    输出的 filepath 是相对于项目根目录的路径，训练脚本会用它拼出绝对路径。
    """
    rows = []
    for class_dir in sorted(DATA_DIR.iterdir()):
        if not class_dir.is_dir():
            continue
        if class_dir.name not in CLASS_NAMES_ZH:
            continue
        for p in sorted(class_dir.iterdir()):
            if p.suffix.lower() in {".jpg", ".jpeg", ".png"}:
                rows.append({
                    # DATA_DIR = 项目根/data/plantvillage_subset，
                    # 再往上两级就是项目根，保存相对路径方便迁移
                    "filepath": str(p.relative_to(DATA_DIR.parent.parent)),
                    "label": class_dir.name,
                    "class_name": CLASS_NAMES_ZH[class_dir.name],
                })

    df = pd.DataFrame(rows)
    if df.empty:
        raise SystemExit(f"No images found under {DATA_DIR}")

    # 第一次切 70% 训练 / 30% 临时；第二次把临时集均分成 15% 验证、15% 测试
    # stratify=df["label"] 保证每个类别在三个子集里的比例一致
    train_df, temp_df = train_test_split(
        df, test_size=0.30, random_state=SEED, stratify=df["label"]
    )
    val_df, test_df = train_test_split(
        temp_df, test_size=0.50, random_state=SEED, stratify=temp_df["label"]
    )
    train_df = train_df.assign(split="train")
    val_df = val_df.assign(split="val")
    test_df = test_df.assign(split="test")

    out = pd.concat([train_df, val_df, test_df]).sort_values(["split", "label", "filepath"])
    out.to_csv(SPLIT_CSV, index=False, encoding="utf-8-sig")

    print(f"total: {len(out)}")
    print(out.groupby(["split", "label"]).size().unstack(fill_value=0))
    print(f"saved: {SPLIT_CSV}")


if __name__ == "__main__":
    main()
