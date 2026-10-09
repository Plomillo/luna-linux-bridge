# External voice E2E harness — reference only

- Upstream: https://github.com/nextain/naia-shell/blob/187dbe5e60d41e2c197e3f3b552e8128f42333fe/packages/shell/e2e/qwen3-asr-voice.spec.ts
- Pinned upstream commit: 187dbe5e60d41e2c197e3f3b552e8128f42333fe
- Upstream license: Apache-2.0; see LICENSE.
- Local status: DOWNLOADED_REFERENCE_NOT_LOUKSNA_VALIDATED.

This file is a reference harness from Naia Shell, not a drop-in Louksna test. It assumes the Naia DOM selectors (.chat-voice-btn, .chat-message.user .message-content), local vLLM at http://localhost:8100 with Qwen/Qwen3-ASR-1.7B, a Korean speech WAV at /tmp/test-ko.wav, and Playwright @playwright/test. It mocks Tauri IPC and therefore does not validate Louksna's native microphone capture, native WebView, or physical audio devices.

Do not count it as an executed E2E test or as CP-07 PASS. Adapt it to the Louksna candidate and run it against the real voice path before closing the voice gate.
