#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""Diebold-Yilmaz 广义方差分解。只依赖 numpy，不访问网络。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

MIN_ROWS = 60
HORIZON = 10
MAX_LAG = 2
RECENT = 5
TARGET = "a_share"


@dataclass
class Connectedness:
    """一次样本上的连通性结果。"""

    theta: pd.DataFrame
    spillover_index: float
    girf: pd.DataFrame
    recent: pd.Series
    lag: int
    observations: int


def connectedness(frame: pd.DataFrame) -> Connectedness | None:
    """对列对齐后的变化序列做 VAR 与广义 FEVD。样本不够时返回 None。"""
    data = frame.dropna(how="any")
    if TARGET not in data.columns or data.shape[1] < 3 or len(data) < MIN_ROWS:
        return None
    z = _standardize(data)
    if z is None:
        return None
    fitted = _select_var(z.to_numpy(dtype=float))
    if fitted is None:
        return None
    beta, sigma, lag, observations = fitted
    k = z.shape[1]
    psis = _ma_coeffs(_coefficients(beta, k, lag), HORIZON)
    theta = _generalized_fevd(psis, sigma)
    girf = _cumulative_girf(psis, sigma)
    labels = list(z.columns)
    return Connectedness(
        theta=pd.DataFrame(theta, index=labels, columns=labels),
        spillover_index=float(100.0 * (1.0 - np.trace(theta) / k)),
        girf=pd.DataFrame(girf, index=labels, columns=labels),
        recent=z.tail(RECENT).mean(),
        lag=lag,
        observations=observations,
    )


def _standardize(frame: pd.DataFrame) -> pd.DataFrame | None:
    std = frame.std(ddof=0).replace(0, np.nan)
    if std.isna().any():
        frame = frame.loc[:, std.notna()]
        std = std.dropna()
    if TARGET not in frame.columns or frame.shape[1] < 3:
        return None
    return (frame - frame.mean()) / std


def _select_var(
    values: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, int, int] | None:
    best = None
    best_aic = np.inf
    for lag in range(1, MAX_LAG + 1):
        fitted = _var_ols(values, lag)
        if fitted is None:
            continue
        beta, sigma, aic, observations = fitted
        if aic < best_aic:
            best_aic = aic
            best = (beta, sigma, lag, observations)
    return best


def _var_ols(
    values: np.ndarray, lag: int
) -> tuple[np.ndarray, np.ndarray, float, int] | None:
    total, k = values.shape
    rows = total - lag
    if rows < k * lag + 2:
        return None
    target = values[lag:]
    design = np.ones((rows, 1 + k * lag))
    for step in range(1, lag + 1):
        design[:, 1 + (step - 1) * k : 1 + step * k] = values[lag - step : total - step]
    beta, _, _, _ = np.linalg.lstsq(design, target, rcond=None)
    resid = target - design @ beta
    sigma = resid.T @ resid / rows
    sigma = sigma + np.eye(k) * 1e-10
    sign, logdet = np.linalg.slogdet(sigma)
    if sign <= 0:
        return None
    nparams = k * (1 + k * lag)
    aic = float(logdet + 2 * nparams / rows)
    return beta, sigma, aic, rows


def _coefficients(beta: np.ndarray, k: int, lag: int) -> list[np.ndarray]:
    return [beta[1 + step * k : 1 + (step + 1) * k, :].T for step in range(lag)]


def _ma_coeffs(coefficients: list[np.ndarray], horizon: int) -> list[np.ndarray]:
    k = coefficients[0].shape[0]
    order = len(coefficients)
    psis = [np.eye(k)]
    for step in range(1, horizon):
        acc = np.zeros((k, k))
        for lag in range(1, min(step, order) + 1):
            acc += coefficients[lag - 1] @ psis[step - lag]
        psis.append(acc)
    return psis


def _generalized_fevd(psis: list[np.ndarray], sigma: np.ndarray) -> np.ndarray:
    k = sigma.shape[0]
    numer = np.zeros((k, k))
    denom = np.zeros(k)
    for psi in psis:
        denom += np.diag(psi @ sigma @ psi.T)
        for column in range(k):
            numer[:, column] += (psi @ sigma[:, column]) ** 2 / sigma[column, column]
    theta = numer / denom[:, None]
    return theta / theta.sum(axis=1, keepdims=True)


def _cumulative_girf(psis: list[np.ndarray], sigma: np.ndarray) -> np.ndarray:
    k = sigma.shape[0]
    scale = np.sqrt(np.diag(sigma))
    out = np.zeros((k, k))
    for psi in psis:
        for column in range(k):
            out[:, column] += psi @ (sigma[:, column] / scale[column])
    return out
