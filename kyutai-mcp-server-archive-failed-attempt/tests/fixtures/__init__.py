"""
Test fixtures, mocks, and test data.

Modules:
- mock_kyutai.py: Kyutai API mocks (TTS, STT, Health)
  Classes: MockKyutaiTTSAPI, MockKyutaiSTTAPI, MockKyutaiHealthAPI, MockConfigFile, MockAudioFile
  Fixtures: mock_tts_api, mock_stt_api, mock_health_api, temp_wav_file, etc.

- test_data.py: Test data and helpers
  Data: SAMPLE_TEXTS, VOICE_CONFIGS, AUDIO_CONFIGS, MODEL_CATALOG, ERROR_SCENARIOS
  Helpers: get_sample_text(), get_voice_config(), get_model_list(), etc.

- mock-mcp.ts: MCP client mock for TypeScript tests
  Classes: MockMCPClient
  Helpers: createMockTTSResponse(), createMockSTTResponse(), setupMockMCPClient()
"""
