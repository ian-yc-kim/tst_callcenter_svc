import os
import time
import logging
import pytest

from tst_callcenter_svc.audio_preprocessing import preprocess_audio


def test_preprocess_audio_valid(tmp_path):
    # Create a dummy .wav file path (file need not exist since processing is simulated)
    dummy_wav = tmp_path / "dummy.wav"
    dummy_wav.write_bytes(b"RIFF\x00\x00\x00\x00")

    result = preprocess_audio(str(dummy_wav))
    assert result["status"] == "processed"
    assert result["processed_file_path"] == str(dummy_wav)


def test_preprocess_audio_invalid_extension(tmp_path):
    # Create a dummy file with an invalid extension
    dummy_file = tmp_path / "dummy.mp3"
    dummy_file.write_bytes(b"dummy content")
    
    with pytest.raises(ValueError) as excinfo:
        preprocess_audio(str(dummy_file))
    assert "Invalid file extension" in str(excinfo.value)


def test_preprocess_audio_fallback(monkeypatch, tmp_path):
    # Simulate failure to import noisereduce to trigger fallback logic
    dummy_wav = tmp_path / "dummy.wav"
    dummy_wav.write_bytes(b"RIFF\x00\x00\x00\x00")

    # Remove 'noisereduce' from sys.modules if it exists
    import sys
    if 'noisereduce' in sys.modules:
        del sys.modules['noisereduce']

    result = preprocess_audio(str(dummy_wav))
    assert result["status"] == "processed"
    assert result["processed_file_path"] == str(dummy_wav)


def test_preprocess_audio_exception(monkeypatch, tmp_path):
    dummy_wav = tmp_path / "dummy.wav"
    dummy_wav.write_bytes(b"RIFF\x00\x00\x00\x00")

    # Create a fake time function that returns a valid start time on first call and then raises an exception
    call_count = [0]
    def fake_time():
        if call_count[0] == 0:
            call_count[0] += 1
            return 100.0
        else:
            raise Exception("Simulated processing error")

    # Patch the time.time function in the audio_preprocessing module directly
    monkeypatch.setattr("tst_callcenter_svc.audio_preprocessing.time.time", fake_time)

    with pytest.raises(Exception) as excinfo:
        preprocess_audio(str(dummy_wav))
    assert "Simulated processing error" in str(excinfo.value)
