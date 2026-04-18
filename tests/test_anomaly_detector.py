from cryptogodfuzzer.anomaly_detector import AnomalyDetector, AnomalyThresholds


def test_detects_latency_and_negative_delta():
    detector = AnomalyDetector(AnomalyThresholds(latency_spike_ms=100, negative_balance_delta=-0.1, balance_jump_ratio=2.0))
    result = detector.detect(100, 250, 10.0, 9.0)
    assert "LATENCY_SPIKE" in result
    assert "NEGATIVE_BALANCE_DELTA" in result


def test_ignores_legit_variation_tag():
    detector = AnomalyDetector()
    result = detector.detect(10, 1000, 1, 100, legit_variations={"known"}, variation_tag="known")
    assert result == []
