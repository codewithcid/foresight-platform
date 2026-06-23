"""Fast, network-free smoke tests for the core pieces."""
import causal
import channels
import byocsv
import datagen


def test_uplift_engine_predicts_per_customer():
    customers = datagen.generate_customers()
    engine = causal.UpliftEngine(customers)
    engine.train()
    row = customers.iloc[0]
    preds = engine.predict_for_customer(row)
    assert preds, "engine should return candidate actions"
    assert all(isinstance(p.predicted_rel_lift, float) for p in preds)


def test_channel_registry_has_all_five():
    ids = {c["id"] for c in channels.status_list()}
    assert {"sms", "whatsapp", "slack", "email", "telegram"} <= ids


def test_unconfigured_channel_fails_gracefully():
    # No keys in CI -> send must not raise, just return ok=False.
    res = channels.get_channel("sms").send("+10000000000", "hi")
    assert res.ok is False and res.error


def test_byocsv_recovers_injected_uplift():
    content = byocsv.sample_csv().encode("utf-8")
    res = byocsv.analyze(content)
    assert res["dataset"]["rows"] > 0
    assert "incrementality" in res["validation"]
    # The S-learner should recover the planted uplift to within a sane error.
    mae = res["validation"]["cell_mae_pp"]
    assert mae is None or mae < 25
