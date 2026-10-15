/**
 * voice.js - Voice Recognition (STT) and Spoken Responses (TTS)
 *
 * Beginner-Friendly Explanation:
 * Many farmers prefer speaking over typing. This script uses the browser's built-in
 * Web Speech API:
 * 1. SpeechRecognition: Listens to the microphone and transcribes spoken words into text.
 * 2. SpeechSynthesis: Speaks out the AI advisory aloud so the farmer can listen.
 * No external paid speech APIs are required; this runs client-side in Google Chrome,
 * Edge, and modern browsers.
 */

class VoiceAssistant {
  constructor(options = {}) {
    this.textarea = options.textarea;
    this.micButton = options.micButton;
    this.statusPill = options.statusPill;
    this.isRecording = false;
    this.currentUtterance = null;
    this.activeSpeakButton = null;

    this.recognition = null;
    this.synth = window.speechSynthesis || null;

    this._initSpeechRecognition();
  }

  _initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.warn("Web Speech API (SpeechRecognition) is not supported in this browser.");
      if (this.micButton) {
        this.micButton.title = "Voice input is not supported in your browser (Try Chrome or Edge).";
      }
      return;
    }

    this.recognition = new SpeechRecognition();
    this.recognition.continuous = false;
    this.recognition.interimResults = false;
    this.recognition.lang = 'en-IN'; // Indian English, also detects common terms

    this.recognition.onstart = () => {
      this.isRecording = true;
      if (this.micButton) this.micButton.classList.add('recording');
      if (this.statusPill) this.statusPill.classList.add('active');
    };

    this.recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      if (this.textarea) {
        const currentText = this.textarea.value.trim();
        this.textarea.value = currentText ? `${currentText} ${transcript}` : transcript;
        this.textarea.dispatchEvent(new Event('input'));
      }
    };

    this.recognition.onerror = (event) => {
      console.error("Speech recognition error:", event.error);
      this.stopListening();
      if (event.error === 'not-allowed') {
        alert("Microphone permission was denied. Please allow microphone access in your browser settings.");
      }
    };

    this.recognition.onend = () => {
      this.stopListening();
    };
  }

  toggleListening() {
    if (!this.recognition) {
      alert("Voice input is not supported in this browser. Please use Google Chrome or Microsoft Edge.");
      return;
    }

    if (this.isRecording) {
      this.recognition.stop();
      this.stopListening();
    } else {
      try {
        this.recognition.start();
      } catch (err) {
        console.warn("Recognition already active or failed to start:", err);
      }
    }
  }

  stopListening() {
    this.isRecording = false;
    if (this.micButton) this.micButton.classList.remove('recording');
    if (this.statusPill) this.statusPill.classList.remove('active');
  }

  /**
   * Speaks out given text using SpeechSynthesis.
   * Cleans markdown symbols and disclaimers so pronunciation sounds clean.
   */
  speakText(text, triggerButton = null) {
    if (!this.synth) {
      alert("Text-to-speech audio is not supported in this browser.");
      return;
    }

    // If currently speaking this exact message, toggle stop
    if (this.synth.speaking && this.activeSpeakButton === triggerButton) {
      this.stopSpeaking();
      return;
    }

    // Stop any ongoing speech
    this.stopSpeaking();

    // Clean text for natural speech: remove markdown symbols and disclaimer footer
    let cleanText = text
      .split('⚠️ **Agricultural Advisory Disclaimer**')[0]
      .replace(/[#*`_~-]/g, ' ')
      .replace(/\[.*?\]/g, '')
      .replace(/\s+/g, ' ')
      .trim();

    if (!cleanText) return;

    this.currentUtterance = new SpeechSynthesisUtterance(cleanText);
    this.currentUtterance.rate = 0.95; // Slightly slower, clear pace
    this.currentUtterance.pitch = 1.0;

    this.activeSpeakButton = triggerButton;
    if (triggerButton) {
      triggerButton.classList.add('speaking');
      triggerButton.innerHTML = '⏹️ Stop';
    }

    this.currentUtterance.onend = () => {
      this._resetSpeakButton();
    };

    this.currentUtterance.onerror = (event) => {
      console.error("SpeechSynthesis error:", event);
      this._resetSpeakButton();
    };

    this.synth.speak(this.currentUtterance);
  }

  stopSpeaking() {
    if (this.synth && this.synth.speaking) {
      this.synth.cancel();
    }
    this._resetSpeakButton();
  }

  _resetSpeakButton() {
    if (this.activeSpeakButton) {
      this.activeSpeakButton.classList.remove('speaking');
      this.activeSpeakButton.innerHTML = '🔊 Listen';
      this.activeSpeakButton = null;
    }
  }
}
