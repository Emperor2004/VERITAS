"""
Automated unit and integration test for the VERITAS Statistical Validation Suite.
"""
from src.statistical_validation import (
    validate_eeoc_boundary,
    validate_sample_size_stability,
    validate_permutation_null_distribution,
    validate_permutation_power,
    validate_knee_point_geometry,
    validate_seed_reproducibility,
)


def test_statistical_validation_eeoc_boundary():
    res = validate_eeoc_boundary()
    assert res["passed"] is True


def test_statistical_validation_sample_size_stability():
    res = validate_sample_size_stability()
    assert res["passed"] is True


def test_statistical_validation_permutation_null_distribution():
    res = validate_permutation_null_distribution(n_trials=20, n_perms=100)
    assert res["passed"] is True


def test_statistical_validation_permutation_power():
    res = validate_permutation_power(n_perms=200)
    assert res["passed"] is True


def test_statistical_validation_knee_point_geometry():
    res = validate_knee_point_geometry()
    assert res["passed"] is True


def test_statistical_validation_seed_reproducibility():
    res = validate_seed_reproducibility()
    assert res["passed"] is True
