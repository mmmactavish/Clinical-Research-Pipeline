"""
样本量/功效计算
支持：两样本均值比较、两样本率比较、生存分析 (log-rank)、等效/非劣效

用法:
    python sample_size.py means --m1 120 --m2 110 --sd 20 --alpha 0.05 --power 0.80
    python sample_size.py proportions --p1 0.30 --p2 0.20 --alpha 0.05 --power 0.80
    python sample_size.py survival --hr 0.70 --event-rate 0.30 --alpha 0.05 --power 0.80

输出: JSON 到 stdout
"""

import json
import sys
import argparse
import math


def _z_alpha(alpha: float, two_sided: bool = True) -> float:
    """标准正态分布分位数 (简化版，使用近似公式)"""
    # 使用 Abramowitz and Stegun 近似
    p = alpha if not two_sided else alpha / 2
    if p <= 0.5:
        # 近似 z 值 (误差 < 0.001 for p in [0.001, 0.5])
        t = math.sqrt(-2 * math.log(p))
        z = t - (2.515517 + 0.802853 * t + 0.010328 * t * t) / \
                (1 + 1.432788 * t + 0.189269 * t * t + 0.001308 * t * t * t)
        return z
    else:
        return -_z_alpha(1 - p, two_sided=False)


def _z_beta(power: float) -> float:
    """Power → Z_β"""
    return _z_alpha(1 - power, two_sided=False)


def sample_size_means(
    mean1: float,
    mean2: float,
    sd: float,
    alpha: float = 0.05,
    power: float = 0.80,
    ratio: float = 1.0,
    dropout: float = 0.0,
    two_sided: bool = True,
) -> dict:
    """
    两样本均值比较 (两独立样本 t-test)

    n = 2 * (Z_α/2 + Z_β)² * σ² / Δ²
    其中 Δ = |mean1 - mean2|
    """
    delta = abs(mean1 - mean2)
    if delta == 0:
        raise ValueError("Effect size (delta) cannot be zero")

    za = _z_alpha(alpha, two_sided)
    zb = _z_beta(power)

    # 每组样本量
    n_per_group = 2 * (za + zb) ** 2 * sd ** 2 / delta ** 2
    n_per_group = math.ceil(n_per_group)

    # 调整两组比例
    n2 = n_per_group
    n1 = math.ceil(n_per_group * ratio)

    # 考虑脱落
    n1_adj = math.ceil(n1 / (1 - dropout)) if dropout > 0 else n1
    n2_adj = math.ceil(n2 / (1 - dropout)) if dropout > 0 else n2
    total = n1_adj + n2_adj

    # 实际功效
    actual_power = _compute_power_means(delta, sd, n1, n2, alpha, two_sided)

    return {
        "design": "Two-sample means comparison (independent t-test)",
        "parameters": {
            "mean_group1": mean1,
            "mean_group2": mean2,
            "delta": round(delta, 4),
            "sd": sd,
            "cohens_d": round(delta / sd, 3) if sd > 0 else None,
            "alpha": alpha,
            "power_target": power,
            "two_sided": two_sided,
            "allocation_ratio": ratio,
            "dropout_rate": dropout,
        },
        "results": {
            "n_per_group_raw": n_per_group,
            "n_group1": n1_adj,
            "n_group2": n2_adj,
            "total_n": total,
            "actual_power": round(actual_power, 4),
        },
        "formula": "n/group = 2*(Z_α/2 + Z_β)² * σ² / Δ²",
        "references": [
            "Chow SC, Wang H, Shao J. Sample Size Calculations in Clinical Research. 2nd ed. 2007.",
        ],
    }


def sample_size_proportions(
    p1: float,
    p2: float,
    alpha: float = 0.05,
    power: float = 0.80,
    ratio: float = 1.0,
    dropout: float = 0.0,
    two_sided: bool = True,
    continuity_correction: bool = True,
) -> dict:
    """
    两样本率比较 (chi-square / Fisher exact)

    n = (Z_α/2 + Z_β)² * [p1(1-p1) + p2(1-p2)] / (p1-p2)²
    带连续性校正: n_corrected = n/4 * [1 + sqrt(1 + 4/(n*|p1-p2|))]²
    """
    delta = abs(p1 - p2)
    if delta == 0:
        raise ValueError("Effect size (delta) cannot be zero")
    if not (0 < p1 < 1 and 0 < p2 < 1):
        raise ValueError("Proportions must be between 0 and 1")

    za = _z_alpha(alpha, two_sided)
    zb = _z_beta(power)

    # 每组样本量
    n_per_group = (za + zb) ** 2 * (p1 * (1 - p1) + p2 * (1 - p2)) / delta ** 2

    # 连续性校正
    if continuity_correction:
        n_per_group = n_per_group / 4 * (1 + math.sqrt(1 + 4 / (n_per_group * delta))) ** 2

    n_per_group = math.ceil(n_per_group)
    n2 = n_per_group
    n1 = math.ceil(n_per_group * ratio)

    n1_adj = math.ceil(n1 / (1 - dropout)) if dropout > 0 else n1
    n2_adj = math.ceil(n2 / (1 - dropout)) if dropout > 0 else n2

    return {
        "design": "Two-sample proportions comparison (chi-square test)",
        "parameters": {
            "p1": p1,
            "p2": p2,
            "delta": round(delta, 4),
            "alpha": alpha,
            "power_target": power,
            "two_sided": two_sided,
            "continuity_correction": continuity_correction,
            "allocation_ratio": ratio,
            "dropout_rate": dropout,
        },
        "results": {
            "n_per_group_raw": n_per_group,
            "n_group1": n1_adj,
            "n_group2": n2_adj,
            "total_n": n1_adj + n2_adj,
        },
        "formula": "n/group = (Z_α/2 + Z_β)² * [p1(1-p1) + p2(1-p2)] / (p1-p2)²",
    }


def sample_size_survival(
    hr: float,
    event_rate: float,
    alpha: float = 0.05,
    power: float = 0.80,
    ratio: float = 1.0,
    dropout: float = 0.0,
    accrual_time: float = 12,
    followup_time: float = 12,
    two_sided: bool = True,
) -> dict:
    """
    生存分析样本量 (log-rank test)

    基于 Schoenfeld 公式:
    Events = (Z_α/2 + Z_β)² / (p1 * p2 * log(HR)²)
    其中 p1, p2 是各组的比例
    总样本量 = Events / 预期事件率
    """
    za = _z_alpha(alpha, two_sided)
    zb = _z_beta(power)

    # 各组比例
    p_grp1 = ratio / (1 + ratio)
    p_grp2 = 1 / (1 + ratio)

    # 所需事件数
    events = (za + zb) ** 2 / (p_grp1 * p_grp2 * (math.log(hr)) ** 2)
    events = math.ceil(events)

    # 总样本量
    total = math.ceil(events / event_rate)

    n1 = math.ceil(total * p_grp1)
    n2 = math.ceil(total * p_grp2)

    n1_adj = math.ceil(n1 / (1 - dropout)) if dropout > 0 else n1
    n2_adj = math.ceil(n2 / (1 - dropout)) if dropout > 0 else n2

    return {
        "design": "Survival analysis (log-rank test)",
        "parameters": {
            "hazard_ratio": hr,
            "event_rate": event_rate,
            "alpha": alpha,
            "power_target": power,
            "two_sided": two_sided,
            "allocation_ratio": ratio,
            "dropout_rate": dropout,
            "accrual_time_months": accrual_time,
            "followup_time_months": followup_time,
            "total_duration_months": accrual_time + followup_time,
        },
        "results": {
            "events_required": events,
            "n_group1": n1_adj,
            "n_group2": n2_adj,
            "total_n": n1_adj + n2_adj,
        },
        "formula": "Events = (Z_α/2 + Z_β)² / (p1*p2*log(HR)²)",
        "references": [
            "Schoenfeld DA. Sample-size formula for the proportional-hazards regression model. Biometrics. 1983.",
            "Freedman LS. Tables of the number of patients required in clinical trials using the logrank test. Stat Med. 1982.",
        ],
    }


def sample_size_equivalence(
    mean1: float,
    mean2: float,
    sd: float,
    margin: float,
    alpha: float = 0.05,
    power: float = 0.80,
    dropout: float = 0.0,
) -> dict:
    """
    等效/非劣效检验样本量

    对等效试验:
    n/group = 2 * (Z_α + Z_β/2)² * σ² / (Δ - |mean1-mean2|)²
    其中 Δ = 等效界值
    """
    delta = abs(mean1 - mean2)
    if delta >= margin:
        sys.stderr.write(f"Warning: Observed difference ({delta}) >= equivalence margin ({margin})\n")

    za = _z_alpha(alpha, two_sided=True)
    zb = _z_beta(power)

    n_per_group = 2 * (za + zb) ** 2 * sd ** 2 / (margin - delta) ** 2
    n_per_group = math.ceil(n_per_group)

    n_adj = math.ceil(n_per_group / (1 - dropout)) if dropout > 0 else n_per_group

    return {
        "design": "Equivalence / Non-inferiority test",
        "parameters": {
            "mean_group1": mean1,
            "mean_group2": mean2,
            "observed_difference": delta,
            "equivalence_margin": margin,
            "sd": sd,
            "alpha": alpha,
            "power_target": power,
            "dropout_rate": dropout,
        },
        "results": {
            "n_per_group": n_adj,
            "total_n": 2 * n_adj,
        },
        "formula": "n/group = 2*(Z_α + Z_β)² * σ² / (Δ - |μ1-μ2|)²",
    }


def _compute_power_means(delta, sd, n1, n2, alpha, two_sided) -> float:
    """计算两样本均值比较的实际功效"""
    za = _z_alpha(alpha, two_sided)
    # Power = P(Z > za - delta / (sd * sqrt(1/n1 + 1/n2)))
    se = sd * math.sqrt(1 / n1 + 1 / n2)
    z_stat = delta / se
    # 简化的 power 计算
    power = 1 - _std_normal_cdf(za - z_stat)
    return max(0.0, min(1.0, power))


def _std_normal_cdf(x: float) -> float:
    """标准正态分布 CDF (近似)"""
    # Abramowitz and Stegun 7.1.26 approximation
    if x < -6:
        return 0.0
    if x > 6:
        return 1.0

    b0 = 0.2316419
    b1 = 0.319381530
    b2 = -0.356563782
    b3 = 1.781477937
    b4 = -1.821255978
    b5 = 1.330274429

    t = 1 / (1 + b0 * abs(x))
    phi = 1 - (1 / math.sqrt(2 * math.pi)) * math.exp(-x * x / 2) * \
          (b1 * t + b2 * t * t + b3 * t * t * t + b4 * t ** 4 + b5 * t ** 5)

    return phi if x >= 0 else 1 - phi


def main():
    parser = argparse.ArgumentParser(description="Sample Size Calculator for CRP")
    subparsers = parser.add_subparsers(dest="design", required=True)

    # 连续变量
    mp = subparsers.add_parser("means", help="Two-sample means comparison")
    mp.add_argument("--m1", type=float, required=True, help="Mean of group 1")
    mp.add_argument("--m2", type=float, required=True, help="Mean of group 2")
    mp.add_argument("--sd", type=float, required=True, help="Standard deviation")
    mp.add_argument("--alpha", type=float, default=0.05)
    mp.add_argument("--power", type=float, default=0.80)
    mp.add_argument("--ratio", type=float, default=1.0, help="Allocation ratio (n1/n2)")
    mp.add_argument("--dropout", type=float, default=0.0, help="Expected dropout rate")
    mp.add_argument("--one-sided", action="store_true", help="One-sided test")

    # 率比较
    pp = subparsers.add_parser("proportions", help="Two-sample proportions comparison")
    pp.add_argument("--p1", type=float, required=True, help="Proportion in group 1")
    pp.add_argument("--p2", type=float, required=True, help="Proportion in group 2")
    pp.add_argument("--alpha", type=float, default=0.05)
    pp.add_argument("--power", type=float, default=0.80)
    pp.add_argument("--ratio", type=float, default=1.0)
    pp.add_argument("--dropout", type=float, default=0.0)
    pp.add_argument("--one-sided", action="store_true")
    pp.add_argument("--no-cc", action="store_true", help="Skip continuity correction")

    # 生存分析
    sp = subparsers.add_parser("survival", help="Survival analysis (log-rank)")
    sp.add_argument("--hr", type=float, required=True, help="Hazard ratio")
    sp.add_argument("--event-rate", type=float, required=True, help="Expected event rate")
    sp.add_argument("--alpha", type=float, default=0.05)
    sp.add_argument("--power", type=float, default=0.80)
    sp.add_argument("--ratio", type=float, default=1.0)
    sp.add_argument("--dropout", type=float, default=0.0)
    sp.add_argument("--accrual", type=float, default=12, help="Accrual time (months)")
    sp.add_argument("--followup", type=float, default=12, help="Follow-up time (months)")
    sp.add_argument("--one-sided", action="store_true")

    # 等效
    ep = subparsers.add_parser("equivalence", help="Equivalence / non-inferiority")
    ep.add_argument("--m1", type=float, required=True, help="Mean of group 1")
    ep.add_argument("--m2", type=float, required=True, help="Mean of group 2")
    ep.add_argument("--sd", type=float, required=True, help="Standard deviation")
    ep.add_argument("--margin", type=float, required=True, help="Equivalence margin")
    ep.add_argument("--alpha", type=float, default=0.05)
    ep.add_argument("--power", type=float, default=0.80)
    ep.add_argument("--dropout", type=float, default=0.0)

    args = parser.parse_args()

    try:
        two_sided = not getattr(args, "one_sided", False)

        if args.design == "means":
            result = sample_size_means(
                mean1=args.m1, mean2=args.m2, sd=args.sd,
                alpha=args.alpha, power=args.power,
                ratio=args.ratio, dropout=args.dropout,
                two_sided=two_sided,
            )
        elif args.design == "proportions":
            result = sample_size_proportions(
                p1=args.p1, p2=args.p2,
                alpha=args.alpha, power=args.power,
                ratio=args.ratio, dropout=args.dropout,
                two_sided=two_sided,
                continuity_correction=not getattr(args, "no_cc", False),
            )
        elif args.design == "survival":
            result = sample_size_survival(
                hr=args.hr, event_rate=args.event_rate,
                alpha=args.alpha, power=args.power,
                ratio=args.ratio, dropout=args.dropout,
                accrual_time=args.accrual, followup_time=args.followup,
                two_sided=two_sided,
            )
        elif args.design == "equivalence":
            result = sample_size_equivalence(
                mean1=args.m1, mean2=args.m2, sd=args.sd,
                margin=args.margin, alpha=args.alpha,
                power=args.power, dropout=args.dropout,
            )
        else:
            sys.stderr.write(f"Unknown design: {args.design}\n")
            sys.exit(1)

        print(json.dumps(result, ensure_ascii=False, indent=2))

    except ValueError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
