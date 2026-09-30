"""The FAKE face engine is for development and browser tests only."""

from app.ai.face_fake import FakeFaceAI
from app.core.config import Settings
from tests.synthetic import image_bytes


def test_fake_engine_is_refused_in_production():
    s = Settings(
        app_env="production",
        jwt_secret="x" * 48,
        cors_origins="https://armor.example",
        armor_embedding_key="k",
        bcrypt_rounds=12,
        face_engine="fake",
    )
    assert any("FACE_ENGINE" in p for p in s.insecure_settings())


def test_fake_engine_cycles_pose_and_keeps_one_person():
    ai = FakeFaceAI()
    faces = [ai.analyze(image_bytes())[0] for _ in range(3)]
    assert [f.yaw for f in faces] == [-15.0, 0.0, 15.0]
    assert all(f.quality_ok for f in faces)
    assert (faces[0].embedding == faces[2].embedding).all()
    assert ai.analyze(b"not an image") == []
    assert ai.available is True
